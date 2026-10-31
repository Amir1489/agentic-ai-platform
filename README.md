# Agentic AI Platform

A bilingual Persian/English Agentic AI workspace built with React, Vite and FastAPI.

## Current status

- Responsive Liquid Glass landing page.
- User registration, login, session validation and logout.
- PostgreSQL-backed user accounts and projects.
- Per-user project isolation.
- Persistent, account-scoped conversations and message history.
- Owner-scoped agent configuration CRUD (draft/active/paused).
- Single-step agent task execution with durable task history and execution audit events.
- Database readiness endpoint and scheduled production smoke-check workflow.
- Optional OpenAI-compatible chat completion integration configured only on the backend.
- Dashboard route and selected-tab persistence across refreshes.
- Frontend deployment through GitHub Pages.
- FastAPI backend deployment through Render.

The Agents dashboard supports agent configuration and bounded single-step model tasks. This is an early runtime MVP, not yet a multi-step autonomous system: tool integrations, background workers, cancellation, cost budgets, approval gates and workflow orchestration remain unimplemented. Settings is still a placeholder. Chat and agent tasks require an OpenAI-compatible provider configured privately on the backend.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

For local development, copy `.env.example` to `.env.local` and set `VITE_API_URL` to your backend URL.

## Backend

```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Set `DATABASE_URL` to PostgreSQL for persistent data. SQLite is intended only for local development and tests.

## Deployment

- Frontend: GitHub Pages.
- Backend: Render (see `render.yaml`).
- Database: Supabase PostgreSQL.

See [agent API and runtime](docs/agents.md), [deployment guide](docs/deployment.md), [authentication notes](docs/auth.md), [projects API](docs/projects.md), [architecture decisions](docs/ARCHITECTURE.md), [product roadmap](docs/ROADMAP.md), and the [engineering progress and release log](docs/PROGRESS.md).

## Important limitations

This is an alpha project. Email verification, password reset, rate limiting, database migrations, monitoring and production abuse protections are not implemented. Browser authentication tokens are currently stored in localStorage; this is convenient for the current prototype but is less resistant to token theft after an XSS vulnerability than secure HttpOnly cookies.

To enable chat replies, set `AI_API_KEY` as a private environment variable on the Render backend. Optionally set `AI_BASE_URL` and `AI_MODEL`. The default model setting is `gpt-4o-mini` with the OpenAI API base URL. API usage may incur separate charges; ChatGPT Free does not include API credits. Never expose these values in frontend `VITE_*` variables.

Never commit database credentials, API keys or session tokens. Do not put private credentials in variables prefixed with `VITE_`; frontend build variables are public.
