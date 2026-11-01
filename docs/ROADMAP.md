# Product Roadmap and Acceptance Criteria

## Product direction

Build a general-audience SaaS workspace for creating and operating AI agents through a visual, no-code builder. The approved product decisions are:
- Audience: general users, with early validation focused on accessible user groups.
- Revenue: Freemium SaaS with server-enforced usage limits; paid tiers only after unit economics are measured.
- Agent creation: Visual Builder as the primary experience.
- Models: multi-provider architecture behind a backend adapter layer.
- Launch: closed, invitation-only beta before any public launch.

See [Product Strategy (Persian)](./fa/PRODUCT_STRATEGY.md) and [Execution Plan (Persian)](./fa/EXECUTION_PLAN.md) for the approved details.

Do not describe the product as fully autonomous until runtime safeguards, permissions, tool execution, audit history and failure handling are implemented and tested.

## Phase 0 — Foundation and security hardening
**Status: partial; verify against current CI and production evidence**

Acceptance criteria:
- Backend API tests and frontend typecheck/build pass on the latest commit.
- Owner-scoped access is tested for all user-owned resources.
- Rate limits, input bounds, session security and CORS are reviewed.
- Database migrations, backup and restore procedures are documented and tested.
- Production health, database readiness and provider capability are reported separately.
- Browser E2E coverage exists for signup, login, agent creation and first task.

## Phase 1 — Visual Agent Builder
**Status: not complete**

Acceptance criteria:
- Users can create and edit agents through forms; no JSON editing or code is required.
- Agent name, description, goal, instructions and model are validated server-side.
- Provider/model choices come from backend configuration, not hard-coded frontend assumptions.
- Draft, active and paused states are clear and enforced.
- Templates and beginner guidance are available.
- Loading, empty, validation, provider-unavailable and error states are accessible.
- API ownership tests and browser flow tests pass.

## Phase 2 — Multi-provider model layer
**Status: partial / requires provider abstraction and additional adapters**

Acceptance criteria:
- A backend Provider Adapter contract isolates model-specific APIs.
- At least two supported providers are integrated before claiming multi-provider availability.
- Provider/model catalogue exposes only configured and permitted choices.
- Secrets remain backend-only and are never returned to clients or logs.
- Timeouts, normalized errors, usage metadata and provider health are handled.
- Contract tests use mocks and do not require live paid accounts in CI.

## Phase 3 — Reliable agent runtime and usage controls
**Status: early single-step execution exists; production safeguards remain**

Acceptance criteria:
- Durable task state machine includes queued, running, succeeded, failed and cancelled states.
- Worker recovery, bounded retries, idempotency and cancellation are tested.
- Per-user concurrency, time, input/output and cost budgets are enforced.
- Execution events are auditable and owner-scoped.
- Provider failures do not create misleading successful task records.

## Phase 4 — Workflow engine and approved tools
**Status: not implemented**

Acceptance criteria:
- Versioned workflows use typed steps and explicit dependencies.
- Timeouts, step limits, budget limits and pause/cancel behavior prevent runaway execution.
- Tool schemas are versioned and inputs/outputs validated.
- Credentials are encrypted and scoped per user.
- Tool allowlists, least privilege, audit events and revocation exist.
- Consequential external actions require explicit human approval.
- SSRF and prompt-injection defenses are tested.

## Phase 5 — SaaS usage, quotas and billing
**Status: not implemented**

Acceptance criteria:
- Usage is metered per user, task, provider and model.
- Free/Pro/Premium entitlements and quotas are enforced in the backend.
- Concurrent requests cannot bypass quotas.
- Cost per successful task and plan margin can be estimated.
- Payment webhooks are verified and idempotent.
- Subscription lifecycle, cancellation and failed-payment behavior are tested.
- No unlimited plan is offered without a measured and safe cost model.

## Phase 6 — Closed beta
**Status: pending**

Acceptance criteria:
- Internal acceptance, security and operational checks pass.
- Initial invitation cohort is 5–10 users, with controlled expansion only after review.
- Onboarding completion, task success, retention, provider errors and cost are measured.
- Feedback intake, support process and rollback procedure are ready.
- No critical security issue remains open.

## Phase 7 — Public launch readiness
**Status: pending; requires a separate go/no-go decision**

Acceptance criteria:
- Load, security, accessibility and mobile usability reviews pass.
- Backup/restore and incident runbooks are tested.
- Monitoring and alerting cover API, database, workers, providers and billing.
- Privacy, terms, retention and account deletion policies are ready.
- Closed-beta evidence supports sustainable unit economics and product value.

## Release rules

1. Implement one bounded workstream at a time in a reviewable branch/PR.
2. Require tests and evidence for every acceptance claim.
3. Distinguish implemented, CI-tested and production-verified states.
4. Do not merge to `main` or deploy without explicit approval.
5. Update `docs/PROGRESS.md` and the relevant product/technical document in the same change set.
