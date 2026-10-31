# Authentication

FastAPI provides registration, login, current-session validation and logout endpoints backed by SQLAlchemy and PostgreSQL.

## Implemented

- `POST /api/auth/register`: creates an account and returns a bearer session token.
- `POST /api/auth/login`: validates credentials and returns a bearer session token.
- `GET /api/auth/me`: validates the current bearer token and returns the user.
- `POST /api/auth/logout`: revokes the current session.
- Passwords are hashed with Argon2.
- Session tokens are cryptographically random. Only SHA-256 token digests are stored in the database.
- Sessions expire after seven days.
- The frontend persists the current token and user in localStorage and validates the session with `/api/auth/me` on application startup.

## Deployment

1. Set `DATABASE_URL` to the PostgreSQL Session Pooler URI supplied by the database provider.
2. Set `CORS_ORIGINS` to the exact frontend origin.
3. Set the GitHub Actions repository variable `VITE_API_URL` to the public HTTPS backend origin, without a trailing slash.
4. Keep database credentials private and outside the frontend build.

## Security limitations

- Email verification and password reset are not implemented.
- Rate limiting, bot protection, monitoring and abuse prevention are not implemented.
- Database schema changes are not managed by migrations yet; startup currently uses SQLAlchemy `create_all`, which does not alter existing tables.
- The frontend stores bearer tokens in localStorage. This is convenient for the current alpha but increases the impact of any cross-site scripting (XSS) vulnerability. A production authentication design should consider secure HttpOnly cookies and appropriate CSRF protections.
- Expired sessions are rejected when used, but there is no scheduled cleanup job for old session rows.

Treat this project as an alpha, not a production-ready identity system. Never commit or share database passwords, bearer tokens or other private credentials.
