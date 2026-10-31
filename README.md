# Agentic AI Platform

A bilingual Persian/English Agentic AI workspace built with React, Vite and FastAPI.

## Current status

- Responsive Liquid Glass landing page.
- User registration, login, session validation and logout.
- PostgreSQL-backed user accounts and projects.
- Per-user project isolation.
- Dashboard route and selected-tab persistence across refreshes.
- Frontend deployment through GitHub Pages.
- FastAPI backend deployment through Render.

The Agents, Conversations and Settings dashboard sections are currently placeholders. AI-agent execution and chat orchestration are not implemented yet.

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

See [deployment guide](docs/deployment.md), [authentication notes](docs/auth.md), and [projects API](docs/projects.md).

## Important limitations

This is an alpha project. Email verification, password reset, rate limiting, database migrations, monitoring and production abuse protections are not implemented. Browser authentication tokens are currently stored in localStorage; this is convenient for the current prototype but is less resistant to token theft after an XSS vulnerability than secure HttpOnly cookies.

Never commit database credentials, API keys or session tokens. Do not put private credentials in variables prefixed with `VITE_`; frontend build variables are public.
