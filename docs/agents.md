# Agents API and Single-Step Runtime

All endpoints require a valid bearer token.

## Agent configuration

- `GET /api/agents` — list agents owned by the current user.
- `POST /api/agents` — create an agent in `draft` state.
- `PUT /api/agents/{agent_id}` — update configuration and lifecycle state.
- `DELETE /api/agents/{agent_id}` — delete an owned agent.

Create/update fields:
- `name`: required, 1–100 characters.
- `description`: optional, up to 500 characters.
- `instructions`: optional system instructions, up to 4,000 characters.
- `model`: provider model identifier, up to 100 characters.
- `status`: `draft`, `active` or `paused` on update.

Every lookup is scoped by the authenticated user's ID. Another user's agent is reported as not found.

## Run a task

1. Configure `AI_API_KEY` privately on the backend.
2. Change the agent to `active`.
3. Send `POST /api/agents/{agent_id}/tasks` with JSON:
   `{"input":"Summarize the supplied topic..." }`

Limits:
- Input: 8,000 characters maximum.
- System instructions: 4,000 characters maximum.
- Output: 12,000 characters maximum.
- Provider HTTP timeout: 45 seconds.

A successful run returns a task with `succeeded` status and the generated output. Provider errors persist a `failed` task and return HTTP 502. Requests made while the provider is not configured return HTTP 503 before a task is created. Only active, owner-owned agents can run.

## Task history and audit

- `GET /api/agents/{agent_id}/tasks` — latest 50 tasks.
- `GET /api/agents/{agent_id}/tasks/{task_id}/events` — ordered execution events.

Current event types are `started`, `succeeded` and `failed`.

## Safety and current limitations

This release only performs one model call per task. It does not execute tools, shell commands, arbitrary code, browser actions or external integrations. It has no background queue, cancellation, retries, per-user token/cost budget, approval workflow or recovery for a process that terminates while a task is marked running. Do not use it for consequential actions or treat it as a production-grade autonomous agent service.
