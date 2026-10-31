# Deployment

The frontend is hosted on GitHub Pages. The FastAPI backend is hosted separately on Render and uses Supabase PostgreSQL.

## Database (Supabase)

1. Open the project's Connect panel.
2. Select the Session Pooler connection method and copy its URI.
3. Store the URI privately as the Render `DATABASE_URL` environment variable.
4. If the database password changes, update Render's environment variable and redeploy the backend.

Never paste database credentials into source files, GitHub commits, frontend variables or public issue trackers.

## Backend (Render)

The root-level `render.yaml` defines the FastAPI web service.

Required environment variables:

- `DATABASE_URL`: private PostgreSQL Session Pooler URI.
- `CORS_ORIGINS`: exact frontend origin, currently `https://amir1489.github.io`.

The health endpoint is `/api/health` and should return a JSON status response.

## Frontend (GitHub Pages)

1. In repository Settings → Secrets and variables → Actions → Variables, set `VITE_API_URL` to the public HTTPS backend origin, without a trailing slash.
2. Run the **Deploy frontend to GitHub Pages** workflow after changing the variable.
3. Confirm the workflow completes successfully.

`VITE_API_URL` is public build-time configuration, not a secret. Never put passwords, private API keys or session tokens in any `VITE_*` variable.

## Smoke test

1. Open the deployed frontend.
2. Register a test account and sign in.
3. Create a project.
4. Refresh and confirm the session and project are restored.
5. Return to Home, refresh, and confirm Home remains selected.
6. Sign in with a second account and verify project isolation.
7. Log out and confirm protected API routes reject the old token.

## Known operational limitations

- Render free services may spin down while idle, causing a delay on the first request.
- SQLAlchemy `create_all` bootstraps tables but does not migrate existing schemas. Add Alembic before evolving production schemas.
- Email verification, password reset, rate limiting, monitoring and production abuse protections are not implemented.
- Browser bearer tokens are stored in localStorage in this alpha release.
