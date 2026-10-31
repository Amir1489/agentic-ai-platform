# Architecture and Engineering Decisions

## Current stack
- Frontend: React 19, TypeScript, Vite, Motion and Lucide.
- Hosting: GitHub Pages.
- Backend: FastAPI + SQLAlchemy.
- Hosting: Render.
- Database: Supabase PostgreSQL.
- Authentication: bearer tokens; token digests stored in the database; Argon2 password hashing.
- AI provider: configurable OpenAI-compatible Chat Completions endpoint, configured only on the backend.

## Request flow
Browser -> GitHub Pages frontend -> HTTPS FastAPI API on Render -> Supabase PostgreSQL.
For chat completion, FastAPI calls the configured AI provider using the private backend key. The browser must never receive the provider key.

## Current API surface
- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET/POST /api/projects`
- `DELETE /api/projects/{project_id}`
- `GET/POST /api/conversations`
- `GET /api/conversations/{conversation_id}/messages`
- `POST /api/conversations/{conversation_id}/messages`
- `DELETE /api/conversations/{conversation_id}`

All project and conversation endpoints require an authenticated session and scope records by owner ID.

## Current security controls
- Password hashes use pwdlib's recommended Argon2 configuration.
- Session tokens are generated with a cryptographically secure random generator.
- Only SHA-256 digests of session tokens are stored in the database.
- Session expiry is checked on authenticated requests.
- Conversation and project ownership is checked server-side.
- AI provider credentials are backend-only.
- CORS origins are configured explicitly.

## Decisions and trade-offs
- Keep AI provider integration behind a small server-side adapter to support compatible providers without exposing keys.
- Keep the frontend provider-agnostic; it calls the platform API, not the model provider directly.
- Keep provider failure from creating a user-only message: generate first, then persist both chat messages in one transaction.
- Keep the initial runtime constrained. Do not introduce arbitrary code/shell execution as an agent capability.
- Use mock providers/tools in CI to keep tests deterministic and free of external billing.
- Add Alembic migrations before evolving production schemas; SQLAlchemy `create_all` is not a migration system.

## Known gaps
- Bearer token is stored in browser localStorage; a secure HttpOnly cookie design is preferred before production.
- No rate limiting or abuse controls yet.
- No email verification or password reset.
- No automated expired-session cleanup.
- No migration framework.
- No confirmed production database/provider smoke test from this repository workflow.
- Agent, tool and workflow runtime are not implemented.
