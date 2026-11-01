# Engineering Progress & Release Log

Last updated: 2026-11-01 (UTC)
Current reviewed branch: `feat/database-backed-auth-rate-limit` (PR #6; stacked on PR #5)
Latest backend CI: [run 41236808395](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236808395)`

## Overall progress

**Estimated implementation progress: 56%** toward the production-oriented product scope defined in [ROADMAP.md](./ROADMAP.md). This is an engineering estimate, not a measured uptime or test-coverage percentage. The landing page, authentication foundation, projects, and persistent chat are implemented; the agent runtime, tool execution, workflow orchestration, and production hardening remain substantial work.

| Workstream | Progress | Evidence / remaining work |
|---|---:|---|
| Landing page and responsive UI | 85% | React/Vite bilingual UI exists; visual/accessibility browser audit remains |
| Authentication and accounts | 68% | Register/login/session/logout tests pass; verification, reset, safer cookie sessions and throttling remain |
| Projects | 75% | User-scoped CRUD and isolation tests exist; pagination and richer project workflows remain |
| Persistent chat | 75% | Conversation/message APIs, ownership, atomic persistence and UI exist; provider config and end-to-end browser tests remain |
| Agent creation/runtime | 63% | Owner-scoped agent CRUD, dashboard controls, single-step model execution, durable task records and audit events exist; queues, cancellation, budgets and tool orchestration remain |
| Tools and integrations | 0% | Not implemented |
| Workflow orchestration | 0% | Multi-step workflows, branching and replay are not implemented; current agent runs are single-step model calls |
| Database reliability/migrations | 45% | Alembic baseline and repeatable migration CI added; backup/restore drills, explicit future revisions and production migration verification remain |
| Security and operations | 33% | Password hashing, hashed session tokens, owner checks, safe capability status and DB readiness; rate limits, secure cookies, monitoring, CSP and abuse controls remain |
| Automated quality gates | 75% | Backend pytest, frontend production build and scheduled frontend/backend/database readiness smoke checks are configured; browser E2E, accessibility, dependency and security scans remain |
| Documentation | 68% | README, architecture, roadmap, agent API guide and progress/release log; operational runbooks and release checklist remain |

## Current verified CI / deployment

- Latest production smoke including public AI capability status: **PASS** — [run 41237125586](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41237125586). Frontend, backend health and database readiness all passed; `/api/capabilities` returned `chat: false`, `agent_tasks: false`.


- Live production smoke: **PASS** — deployed GitHub Pages frontend returned the expected app shell, Render `/api/health` passed, and Render `/api/ready` confirmed database connectivity — [run 41237092058](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41237092058).


- Persisted agent task history UI build and GitHub Pages deployment: **PASS** — [run 41236934388](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236934388).


- Alembic baseline repeated twice against a clean SQLite database and backend API suite: **PASS** — [run 41236687579](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236687579).


- Latest backend API suite (including capability status, per-agent model selection, task success/failure audit, and whitespace validation): **PASS** — [run 41236572082](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236572082).
- Settings overview frontend build and Pages deployment: **PASS** — [run 41236476001](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236476001).


- Agent runtime backend tests, including success/failure persistence and audit events: **PASS** — [run 41236359157](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236359157).
- Agent dashboard TypeScript production build and GitHub Pages deployment: **PASS** — [run 41236314384](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236314384).
- Earlier readiness endpoint tests: **PASS** — [run 41236189102](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236189102).


- Agent CRUD backend tests: **PASS** — [run 41236112302](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41236112302), including ownership isolation and lifecycle state updates.
- Earlier CI configuration checks: backend tests and frontend Pages deploy **PASS** — [backend run 41235967420](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41235967420), [frontend run 41235963845](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41235963845).
- Agent dashboard UI build is currently queued/in progress; do not count it as passed until completed.

For commit `fe68d11`:
- Backend API tests: **PASS** — [run 41235453094](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41235453094)
- Frontend build and GitHub Pages deployment: **PASS** — [run 41235453092](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41235453092)

The same commit is on the default branch. CI success proves the automated tests/build completed; it does **not** prove the production Render service, Supabase credentials, AI provider, or every browser interaction is healthy. Those require live runtime checks and credentials/permissions that are not available to the repository workflow.

## Release log

### 2026-11-01 — Aggregate workspace metrics endpoint
- Added authenticated `GET /api/agents/summary` with database-side counts for active agents and successful tasks, scoped to the current user.
- Replaced the dashboard's per-agent task-history fan-out with one summary request, avoiding N+1 HTTP requests and ensuring successful-task totals are not truncated by the per-agent 50-item history limit.
- Added API assertions for empty summaries, successful task counts and owner isolation.
- Backend and frontend CI are required; no production deployment or merge is performed from this branch.
- Rollback: revert the summary endpoint, its tests and the dashboard consumer together.


### 2026-11-01 — Workspace dashboard live metrics
- Replaced the misleading dashboard preview label with workspace wording for authenticated users.
- Dashboard overview now fetches the signed-in user's agents and their persisted task histories through owner-scoped API routes.
- Active-agent and successful-task counters now display actual API-derived values; they show a neutral placeholder when data cannot be verified rather than fabricated zeroes.
- Added loading/sync feedback and kept the unauthenticated local preview clearly labelled.
- Frontend CI is triggered by this change; no local build or production deployment is claimed.
- Change is isolated on `feat/landing-page-product-clarity`; rollback is a revert of the dashboard commit.


### 2026-11-01 — Landing page product-scope clarity (branch validation pending)
- Replaced promotional copy that implied tool integrations and complex autonomous execution with an accurate description of the current bounded MVP.
- Added bilingual responsive cards for agent management, single-step supervised runs, and persistent project/conversation/task history.
- Added an explicit note that external tools and multi-step workflows remain roadmap items.
- Fixed the primary landing-page CTA so signed-out visitors are sent to authentication instead of the protected dashboard.
- Added a dedicated GitHub Actions frontend build workflow for pull requests; it runs TypeScript checking and the Vite production build on Node 22.
- Latest production smoke on `main` (run [41267114702](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41267114702), 2026-11-01) passed the deployed frontend, API health, and database readiness checks. The capability endpoint reported `chat: false` and `agent_tasks: false`; live AI execution is therefore unavailable until the owner configures a provider privately.
- The frontend build workflow also runs on `feat/**` branches so this PR can receive a TypeScript/Vite build result before review.
- Changes are isolated on `feat/landing-page-product-clarity`; no merge or production deployment has occurred. Frontend CI is pending.
- Rollback: revert the commits on this feature branch; `main` and the live site remain unchanged.


### 2026-10-31 — Production AI capability check
- Added a secret-safe smoke check for `/api/capabilities`.
- Production frontend, backend health and database readiness all passed.
- Production reports `chat: false` and `agent_tasks: false`: no private `AI_API_KEY` is configured on the Render backend at the time of this check. No model calls can succeed until the owner configures a provider key privately in Render; no key was requested or exposed.



### 2026-10-31 — Live production smoke verification
- Triggered the production smoke workflow on the latest monitoring configuration.
- Deployed frontend responded with the expected root app shell.
- Render backend health endpoint returned the expected service status.
- Render database readiness endpoint returned ready/reachable.
- This verifies service and database connectivity at the time of the run; it does not verify live AI provider credentials or actual model execution.



### 2026-10-31 — Persisted task history in dashboard
- Agent cards now fetch and display recent persisted task runs after reload.
- New task results are added to the local task-history view immediately after successful execution.
- Added responsive styling for task input/output and history records.
- Frontend production build and GitHub Pages deployment passed in run 41236934388.



### 2026-10-31 — Database migration baseline
- Added Alembic configuration, environment, initial idempotent schema baseline and revision template.
- Render startup now runs `alembic upgrade head` before Uvicorn.
- Backend CI runs the baseline twice against a clean SQLite database, then runs the API suite; all steps passed in run 41236687579.
- Existing installations are adopted without dropping tables. The baseline is intentionally forward-only; future schema changes require explicit revisions and backups.



### 2026-10-31 — Settings overview and runtime validation hardening
- Added a safe `/api/capabilities` endpoint exposing only whether chat and agent tasks are configured; no secrets or provider URLs are returned.
- Added a dashboard Settings overview for account email, security notes and AI provider configuration state.
- Agent task requests now use the agent's selected model rather than silently falling back to the global model.
- Fixed blank model identifier validation and added regression coverage.
- Latest backend suite passed in run 41236572082; frontend deployment passed in run 41236476001.



### 2026-10-31 — Agent task runtime CI verification
- Backend test suite passed for task success, task failure persistence, ownership and audit-event ordering.
- Frontend TypeScript/Vite production build and Pages deployment passed with agent task controls.
- Live provider execution remains unverified because backend provider credentials are not available to CI.



### 2026-10-31 — First bounded agent execution path
- Added durable agent task records and append-only started/succeeded/failed event records.
- Added `POST /api/agents/{id}/tasks` for a single-step model execution; only owner-owned agents in `active` state can run.
- Added task history and per-task event history endpoints.
- Agent instructions and description are passed as a bounded system prompt; user input is capped at 8,000 characters and output at 12,000 characters.
- Provider-unavailable requests are rejected before task creation; provider failures mark persisted tasks as failed.
- No tools, shell execution, background worker, retries, cancellation, cost budget or multi-step planning are available yet.
- Backend and frontend CI for the new execution path is pending final runs.



### 2026-10-31 — Database readiness and production monitoring
- Added `/api/ready`, a database connectivity probe that runs `SELECT 1` and returns HTTP 503 when the database is unavailable.
- Added readiness coverage to backend API tests.
- Extended the scheduled production smoke workflow to verify frontend, backend health and backend database readiness every six hours.
- The scheduled smoke workflow has not yet been observed running; live production readiness remains unverified.



### 2026-10-31 — Agent management foundation
- Added persistent Agent model and authenticated, owner-scoped CRUD endpoints at `/api/agents`.
- Added draft/active/paused lifecycle metadata; updates validate and persist configuration.
- Added agent dashboard panel for create, list, status toggle and delete.
- Added backend tests covering user isolation and lifecycle changes.
- Agent activation is configuration state only: no agent runtime or external tool execution exists yet.
- Backend API tests passed in run 41236112302; frontend build is pending in run 41236136257.



### 2026-10-31 — Chat stability and CI verification
- Updated `frontend/src/ChatPanel.tsx` to coordinate create/send/delete actions, disable conflicting controls, avoid duplicate submissions, and make deletion state explicit.
- Preserved cancellation protection when switching between conversation histories.
- Verified backend tests and frontend Pages deployment both pass on `fe68d11`.
- No live AI response is claimed: Render must have a valid private `AI_API_KEY` and provider configuration.

### 2026-10-31 — Atomic chat persistence
- Provider response is generated before writing the user/assistant pair.
- User and assistant messages are committed together after provider success.
- Conversation activity timestamp is advanced on successful send.
- Added tests for ownership isolation, provider-not-configured behavior, atomic failure behavior, and successful message persistence.
- Backend tests and frontend deployment passed on `dbae1f0`.

## Rules for recording progress
1. Every meaningful change must update this file and the relevant technical document in the same change set.
2. Percentages are estimates against the scope in `ROADMAP.md`; update only when acceptance criteria have evidence.
3. Record commit SHA, CI run links, test outcome, deployment outcome, known limitations, and rollback note.
4. Never label a feature complete based only on UI appearance. Require API tests and, where applicable, browser/runtime verification.
5. Keep secrets, access tokens, database URLs and personal data out of logs and Git history.

## Current blockers / external dependencies
- The AI provider is not confirmed configured in Render. The user must not paste API keys into chat or commit them.
- Render and Supabase private control-plane settings are not available through the current GitHub repository integration.
- Full production browser tests need an available browser automation runtime and a test environment/account.
- API provider usage may incur separate charges. ChatGPT Free does not include API credits.


## 2026-11-01 — Phase 0 security review started
- Created isolated branch `chore/phase-0-security-hardening` from `feat/landing-page-product-clarity`.
- Added a regression test for unauthenticated access and cross-account isolation of Agent Task details and event history.
- Updated authentication documentation to accurately describe the current Alembic baseline and startup `create_all` behavior.
- Recorded known security gaps: missing rate limiting, localStorage bearer-token exposure, account lifecycle gaps and operational monitoring.
- Added a security review document with priorities, evidence, scope boundaries and phase-exit criteria.
- No production settings, secrets, database schema or deployed service were changed.
- Backend API tests: **PASS** — [run 41278858744](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41278858744).
- Frontend build checks: **PASS** — [run 41278858742](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41278858742).
- Both workflows passed on commit `e852d6d1c17f34675095b475f8b7ebe4b78c3bf4`; this validates the backend test suite and frontend production build, not a security audit or production deployment.


### 2026-11-01 — Shared database-backed authentication rate limits
- Added atomic fixed-window counters stored in the application database for registration and login, shared across backend processes and instances using the same database.
- Registration is limited to 20 attempts per client address per hour; login is limited to 5 attempts per account and client address per 15-minute window.
- Persisted bucket identifiers are SHA-256 hashes; raw email addresses and client addresses are not stored in the rate-limit table.
- Rejected requests return HTTP 429 with a Retry-After header. If the limiter storage is unavailable or the database dialect is unsupported, authentication fails closed with HTTP 503.
- Added Alembic revision `0002_auth_rate_limits`; it safely handles the existing metadata-driven initial baseline on fresh databases.
- Added backend tests for registration and login throttling. Backend API tests: **PASS** — [run 41279651417](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41279651417). Frontend build checks: **PASS** — [run 41279651386](https://github.com/Amir1489/agentic-ai-platform/actions/runs/41279651386).
- Verified on implementation commit `d6719cfd91d0434a96842c42da1834c138fab22c`; documentation is synchronized in PR #6. No production deployment or merge is claimed.
- Known limitation: fixed-window boundaries can permit a short burst across adjacent windows; proxy-derived client IP headers are intentionally not trusted until trusted-proxy configuration is explicitly designed.
- Rollback: revert the route integration, limiter module, model, tests and migration together; do not downgrade a live database without an approved data/rollback plan.
