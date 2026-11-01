# Secure Cookie Authentication Migration Proposal

**Status:** Architecture proposal only — not implemented  
**Date:** 2026-11-01  
**Scope:** Replace browser-persisted Bearer tokens with server-managed HttpOnly session cookies.

## 1. Current state and decision

The current frontend is hosted at `https://amir1489.github.io` and the API is hosted separately on Render. The frontend stores the session Bearer token in `localStorage` and sends it in the `Authorization` header.

A direct switch to cross-site cookies between `github.io` and a Render `onrender.com` hostname is not a reliable production design. It depends on third-party-cookie behavior, which browsers and privacy settings may block.

**Decision:** Before enabling cookie authentication in production, place the frontend and API on HTTPS subdomains of one registrable domain controlled by the project owner. Example placeholders:

- Frontend: `https://app.example.com`
- API: `https://api.example.com`

These are examples, not configured domains. Keep the existing deployment and Bearer flow until the custom-domain prerequisite is available and verified.

## 2. Cookie contract

After the domain prerequisite is met:

- Use a host-only session cookie named `__Host-agentic_session`.
- Set `Secure`, `HttpOnly`, `Path=/`, and `SameSite=Lax`; set a maximum age no longer than the existing seven-day session lifetime.
- Do not set a `Domain` attribute. The `__Host-` prefix requires Secure, Path=/ and no Domain attribute.
- Continue storing only a cryptographic digest of the random session token in the database; never store or log the raw token.
- The cookie is scoped to the API host. The frontend must not attempt to read it.
- Frontend requests to the API use Fetch `credentials: 'include'`; no session token is persisted in localStorage, sessionStorage, URLs, or frontend state beyond transient request handling.

## 3. CSRF and browser-origin protections

HttpOnly prevents JavaScript from reading the session cookie; it does not by itself prevent CSRF.

Use all of the following:

1. Exact allowlist validation of the `Origin` header on every state-changing request. Reject unexpected or missing origins where browser-origin validation is required; do not fall back to wildcard matching.
2. A session-bound synchronizer token. A proposed implementation is a token derived with a server-only HMAC key from the authenticated session secret. Expose it through a credentialed `GET /api/auth/csrf` response with `Cache-Control: no-store`; send it in `X-CSRF-Token` on unsafe methods. The API validates the header against the API-host CSRF cookie and the session-bound expected value using constant-time comparison.
3. Use a host-only `__Host-agentic_csrf` cookie with `Secure`, `SameSite=Lax`, and `Path=/`; it is not HttpOnly because the browser client needs a token value, but the frontend obtains the value from the CSRF endpoint response rather than trying to read an API-host cookie.
4. Require CSRF protection for authenticated state-changing requests, including logout. Apply strict Origin validation to login and registration as well to reduce login-CSRF risk.
5. Never treat CORS as a substitute for CSRF validation.

The exact CSRF token derivation and rotation behavior must be finalized in implementation review and covered by tests before rollout.

## 4. CORS and Fetch contract

For the production frontend origin:

- Configure an exact `CORS_ORIGINS` allowlist, e.g. `https://app.example.com`.
- Enable credentialed CORS only for those exact origins.
- Never combine `Access-Control-Allow-Credentials: true` with wildcard origins.
- Allow only required methods and headers, including `Content-Type` and `X-CSRF-Token`; do not expose unnecessary response headers.
- Handle OPTIONS preflight requests correctly.
- Use `credentials: 'include'` for login, registration, CSRF bootstrap, logout, and all authenticated API requests.
- Keep the cookie host-only on the API subdomain; do not broaden it to the parent domain.

For local development, prefer a same-origin Vite development proxy for `/api` rather than weakening production cookie or CORS settings.

## 5. API and session behavior

Target behavior:

- `POST /api/auth/register` and `POST /api/auth/login`: validate credentials, issue the existing random server-side session, set the HttpOnly cookie, and return only the public user plus the CSRF bootstrap material needed by the client. Do not return the session token in JSON.
- `GET /api/auth/me`: authenticate from the cookie.
- `GET /api/auth/csrf`: return a non-cacheable CSRF token for the current session and set/refresh the matching API-host CSRF cookie.
- `POST /api/auth/logout`: require CSRF validation, revoke the database session, and clear session and CSRF cookies using matching cookie attributes.
- All protected routers must use the same cookie-aware authentication dependency and retain existing owner-scoped authorization checks.
- Keep the seven-day absolute expiry unless a separate session-lifetime decision is approved. Consider idle expiry and session rotation as later hardening, not implicit scope.

## 6. Migration and rollout sequence

1. Owner obtains and controls a custom domain; configure HTTPS for both app and API subdomains.
2. Verify the deployed frontend origin and API origin are same-site and that TLS, DNS, and Render/GitHub Pages custom-domain routing work.
3. Implement cookie issuance/validation, CSRF, exact Origin validation, credentialed CORS, and migration tests behind an explicit rollout gate.
4. Update every frontend API call to include credentials; remove Bearer-token reads/writes and clear legacy `agentic-auth-token` and `agentic-auth-user` localStorage entries after successful cookie sign-in.
5. Require existing users to sign in again at cutover. Do not silently transmit or migrate old localStorage tokens as a shortcut.
6. Run the full acceptance matrix below in a staging environment before enabling the cookie mode in production.
7. Monitor authentication failures, CSRF rejections, CORS preflights, and session revocations without logging credentials or token values.
8. After a defined observation window, remove legacy Bearer authentication and update the auth documentation.

No DNS, hosting, custom-domain, production environment, or authentication-code changes are authorized by this proposal.

## 7. Acceptance and security test matrix

- Login and registration set the expected HttpOnly, Secure, SameSite, Path and host-only cookie attributes.
- Session cookie is absent from JavaScript-visible storage and is never returned in JSON.
- Valid cookie authenticates `/api/auth/me` and all protected routers.
- Expired, revoked, malformed, and absent cookies are rejected.
- Logout revokes the session and clears both cookies.
- Valid CSRF token succeeds; missing, incorrect, stale, and cross-session tokens fail.
- Unexpected Origin values are rejected for login, registration, and every state-changing route.
- Untrusted origins cannot read credentialed responses; wildcard CORS is absent.
- Credentialed preflight succeeds only for the configured frontend origin and required headers.
- Cross-account resource isolation tests continue to pass.
- Rate-limit tests continue to pass.
- Migration upgrade tests pass on both a clean database and a database at the previous Alembic revision.
- Browser tests cover current Chromium, Firefox, and WebKit behavior with third-party cookies disabled.

## 8. Rollback and operational safeguards

- Keep the current Bearer implementation unchanged until cookie mode passes staging acceptance.
- Make cookie mode an explicit backend configuration gate; do not infer it from request headers.
- A rollback may restore the prior Bearer flow while existing server-side sessions remain valid. Do not drop session records or reverse schema changes without a separate reviewed migration.
- Do not log Cookie, Set-Cookie, Authorization, CSRF token, password, or session-token values.
- Keep provider keys and database credentials exclusively in backend secret storage.

## 9. Open prerequisites

- Project-owner decision and access to a custom domain.
- DNS and TLS configuration for app and API subdomains.
- Confirmed hosting support for the selected custom-domain topology.
- Final CSRF token derivation/rotation review.
- Staging environment and browser automation coverage.

**Release gate:** Do not enable cookie authentication or claim the localStorage risk is resolved until all prerequisites and acceptance tests are satisfied.
