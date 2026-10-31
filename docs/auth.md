# Authentication — phase 3

FastAPI implements register, login, me and logout endpoints backed by SQLAlchemy/PostgreSQL.
Passwords are hashed with Argon2. Bearer session tokens are cryptographically random; only SHA-256 digests are stored in the database. Sessions expire after 7 days and logout revokes the session.

## Important deployment steps
1. Provision a PostgreSQL database and a backend HTTPS host.
2. Set DATABASE_URL and CORS_ORIGINS as backend environment variables (do not commit secrets).
3. Set VITE_API_URL as a GitHub Actions variable when building the frontend; it must point to your backend HTTPS URL.
4. Keep the backend private credentials outside GitHub Pages.
5. The initial version uses SQLAlchemy create_all for bootstrapping; use Alembic migrations before evolving production schemas.

## Security and limitations
- API is not deployed by GitHub Pages; the login form cannot connect until the backend is hosted.
- Frontend holds bearer tokens in memory only; refreshing the page signs the user out. This reduces persistence risk but is not a complete production auth architecture.
- Password reset and email verification are not implemented yet.
- Rate limiting, bot protection, monitoring, migrations and abuse prevention must be added before a public production launch.
- Never use SQLite on ephemeral backend hosting for real accounts.
