# Projects API — Phase 3

Authenticated routes (Bearer token):

- `GET /api/projects` lists only the current user's projects.
- `POST /api/projects` with JSON `{ "name": "My project" }` creates a project.
- `DELETE /api/projects/{id}` deletes only a project owned by the current user; other IDs return 404.

The dashboard uses these endpoints only after login AND when `VITE_API_URL` is set. Otherwise it remains a clearly labelled browser-local preview.

## Deployment

1. Deploy the FastAPI backend with a persistent PostgreSQL database and HTTPS.
2. Set backend `DATABASE_URL` and `CORS_ORIGINS=https://amir1489.github.io`.
3. In GitHub repository Settings > Secrets and variables > Actions > Variables, set `VITE_API_URL` to the public HTTPS backend origin, without a trailing slash.
4. Trigger the frontend deploy workflow again after setting the variable.
5. Test registration, login, project creation and deletion with two distinct users to confirm isolation.

Do not place database passwords, API keys or bearer tokens in GitHub Actions variables prefixed with `VITE_`; these values become public frontend bundle data. Only the public backend URL belongs there.

Current limitations: the backend has not been deployed, migrations and production abuse protections are pending, and browser sessions are in-memory only.
