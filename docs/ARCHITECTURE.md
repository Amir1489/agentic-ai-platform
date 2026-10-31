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


## Agent management API (added 2026-10-31)
- `GET /api/agents`: list the authenticated user's agents.
- `POST /api/agents`: create an agent in `draft` state.
- `PUT /api/agents/{id}`: update name, description, instructions, model and lifecycle state (`draft`, `active`, `paused`).
- `DELETE /api/agents/{id}`: delete an owned agent.
- Every endpoint requires a valid bearer session and scopes reads/writes by `owner_id`.
- Important boundary: `active` is currently metadata only. It does not launch a worker or execute model/tool actions; runtime is a later roadmap phase.


## Health and readiness
- `GET /api/health` is a process-level health response and does not verify dependencies.
- `GET /api/ready` performs a lightweight `SELECT 1` using the configured SQLAlchemy engine and returns HTTP 503 on database errors. It does not expose connection strings or credentials.


## Agent task execution (single-step MVP)
- `POST /api/agents/{agent_id}/tasks` runs one model response for an owned agent whose status is `active`.
- Input is capped at 8,000 characters; generated output is capped at 12,000 characters; provider timeout is 45 seconds.
- Task records persist `running`, `succeeded` or `failed` status. Events record `started`, `succeeded` or `failed` transitions.
- `GET /api/agents/{agent_id}/tasks` returns up to 50 recent task records.
- `GET /api/agents/{agent_id}/tasks/{task_id}/events` returns the task audit trail.
- This is deliberately not a general-purpose tool runner: no shell, code interpreter, network fetch, external integrations or arbitrary tool execution is available.
- Known runtime gaps: synchronous HTTP execution, no worker queue, no cancellation, no cost/token budgets, no retry policy, no stuck-running recovery and no human approval workflow.


## Public capability status
- `GET /api/capabilities` returns only booleans for `chat` and `agent_tasks`, derived from whether a private `AI_API_KEY` is configured.
- It never returns the key, base URL, provider response or secret values. The settings screen uses it to display whether AI features are configured.


## Database migrations
- Alembic is configured under `backend/migrations`.
- The initial revision uses `Base.metadata.create_all` as an idempotent adoption baseline so existing installations are not dropped or recreated; it creates missing tables on a fresh database.
- Render runs `alembic upgrade head` before starting Uvicorn.
- The initial baseline is forward-only. Future schema changes must be implemented as explicit Alembic revisions; `create_all` remains a compatibility fallback and does not alter existing columns.
