# Product Roadmap and Acceptance Criteria

## Product direction
Build a reliable bilingual (Persian/English) Agentic AI workspace where users can create agents, connect approved tools, run supervised tasks, inspect execution history, and manage projects and conversations.

The platform must not be described as a fully autonomous agent system until the runtime, permissions, tool execution, audit history, and failure handling exist and are tested.

## Phase 0 — Foundation and deployment
**Status: implemented with remaining operational verification**

Acceptance criteria:
- React/Vite frontend builds in CI.
- FastAPI backend tests pass in CI.
- GitHub Pages deployment completes.
- [x] Render health endpoint responds successfully in production (scheduled smoke workflow configured; live check pending).
- [x] Database readiness endpoint is implemented and covered by backend tests; live Supabase connectivity remains to be confirmed.
- Supabase connection is verified without exposing credentials.
- CORS allows only explicitly configured frontend origins.

## Phase 1 — Accounts, projects, conversations
**Status: core implemented; hardening remains**

Acceptance criteria:
- Registration rejects invalid input and duplicate accounts.
- Passwords are hashed; raw passwords are never stored.
- Login, current-user lookup, logout and expired-session behavior are tested.
- Users cannot list, read, modify or delete another user's resources.
- Project CRUD persists across sessions.
- Conversation history persists; provider failures do not leave orphan user messages.
- UI handles loading, empty, error, retry and concurrent-action states.
- Add email verification, password reset, session revocation, rate limiting and secure cookie strategy before production.

## Phase 2 — Agent management
**Status: partially implemented**

Acceptance criteria:
- [x] Create, list, edit, pause, resume and delete agent configuration records.
- [ ] Add full form validation, pagination and robust browser E2E coverage.
- Agent configuration is validated server-side and scoped to its owner.
- Agent identity, model selection, system instructions, enabled tools and limits are persisted.
- Draft and active states are distinct.
- Dangerous or external actions require explicit per-action approval.
- UI has empty/loading/error states and clear validation.

## Phase 3 — Agent runtime and task execution
**Status: not implemented**

Acceptance criteria:
- Backend task state machine: queued, running, awaiting approval, succeeded, failed, cancelled.
- Durable task records and append-only execution events.
- Bounded execution time, token/cost budgets, retries with backoff and cancellation.
- Idempotency protections for retried operations.
- No arbitrary shell/code execution in the initial release.
- Tool allowlists, input validation and least-privilege credentials.
- Clear trace of model decisions, tool calls, outputs and failures.
- Human approval gates for sending messages, publishing, deleting, spending or other consequential actions.

## Phase 4 — Tool registry and integrations
**Status: not implemented**

Acceptance criteria:
- Versioned tool schemas with typed inputs/outputs.
- Per-user authorization and encrypted credential storage.
- Tool permission scopes and revocation.
- Timeouts, quotas, structured errors and audit events.
- Mock tools for CI; integration tests never depend on real external accounts.
- SSRF and prompt-injection defenses for tools that fetch external content.

## Phase 5 — Workflow orchestration
**Status: not implemented**

Acceptance criteria:
- Users can compose tasks from validated steps.
- Explicit branching, retries, timeouts and approval nodes.
- Persisted workflow versions and run history.
- Execution limits prevent infinite loops and runaway costs.
- Resume/replay behavior is deterministic where possible.

## Phase 6 — Settings, observability and operations
**Status: partial / not implemented**

Acceptance criteria:
- Profile, language, appearance, session and provider settings.
- No secret is returned to the browser after saving.
- Structured logs exclude credentials and sensitive content by default.
- Health/readiness checks distinguish API health from database/provider readiness.
- Error monitoring, metrics, alerts, backup and restore drills.
- Data export and account deletion policy.

## Phase 7 — Release readiness
**Status: pending**

Required checks:
- Backend unit/API/integration suite.
- Frontend typecheck and production build.
- Browser E2E tests for signup, login, logout, project CRUD, chat history and responsive navigation.
- Accessibility audit (keyboard, labels, contrast, reduced motion).
- Security review (authorization, input validation, CORS, rate limits, secrets, dependency audit).
- Performance audit (bundle size, API latency, DB query patterns, pagination).
- Production smoke tests against live frontend/backend/database.
- Document known limitations, rollback procedure and release notes.

## Prioritization
1. Fix correctness/security issues in existing foundation.
2. Add reproducible tests and documented CI evidence.
3. Implement agent CRUD and the runtime with strict permission boundaries.
4. Add tools and workflows after runtime safeguards exist.
5. Complete settings and production hardening.
6. Perform end-to-end, security, accessibility and performance release checks.
