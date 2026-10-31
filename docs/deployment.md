# Deploy the API and database

The frontend is hosted on GitHub Pages. The backend needs its own HTTPS server and persistent PostgreSQL database.

## Database
Create a PostgreSQL database with your chosen provider. Copy its connection URL **privately**; do not paste it into the repository or frontend settings.

## Render
1. In Render, choose New > Blueprint and connect this GitHub repository.
2. Render will read the root-level `render.yaml` and configure a Python web service from the `backend` directory.
3. Supply `DATABASE_URL` as a private environment variable. Use a valid PostgreSQL connection URL and SSL according to the provider's documentation.
4. Set `CORS_ORIGINS` to `https://amir1489.github.io` (already provided as a default in the Blueprint).
5. Deploy the service, then check `https://YOUR-RENDER-SERVICE/api/health`. It should return `{"status":"ok","service":"agentic-ai-platform"}`.

## Connect frontend
1. In GitHub repository Settings > Secrets and variables > Actions > Variables, add `VITE_API_URL` with the **public HTTPS origin** of the Render backend, without a trailing slash. This is not a secret.
2. Re-run **Deploy frontend to GitHub Pages**. The build embeds `VITE_API_URL`.
3. Register a test account, log in, create a project, refresh, and verify persistence. Try a second test account and verify it cannot see the first user's projects.

## Troubleshooting
- **Backend fails to start**: inspect Render logs; verify `DATABASE_URL` and database network/SSL settings.
- **CORS blocked**: verify `CORS_ORIGINS` matches the exact frontend origin (scheme and hostname).
- **Frontend says backend not configured**: verify `VITE_API_URL` is a GitHub Actions *variable* and re-run the frontend workflow.
- **503 or delayed first request**: check service health and any idle/spin-down policy.
- **Tables missing**: check database permissions and backend startup logs.

## Production limitations
The current application is an alpha. Before public registration, add email verification, password reset, rate limiting, database migrations, monitoring and a durable session strategy. Database tables are currently bootstrapped with SQLAlchemy `create_all`, which does not migrate existing tables. Review hosting costs and service plan availability in your provider account; no free tier is assumed.
