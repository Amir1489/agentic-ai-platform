# Projects API

The authenticated project API is deployed with the FastAPI backend.

All endpoints require an `Authorization: Bearer <token>` header.

- `GET /api/projects` lists only the current user's projects.
- `POST /api/projects` with JSON `{ "name": "My project" }` creates a project.
- `DELETE /api/projects/{id}` deletes only a project owned by the current user. A project belonging to another user returns 404.

The dashboard uses the API after login when `VITE_API_URL` is configured. Without an authenticated session and backend URL, it uses a browser-local preview.

## Verification

1. Register or sign in.
2. Create a project and refresh the page.
3. Confirm that the project remains available.
4. Sign in with a second account and confirm that the first account's projects are not visible or deletable.

Do not place database passwords, API keys or bearer tokens in GitHub Actions variables prefixed with `VITE_`; those values become public frontend bundle data. Only the public backend URL belongs there.

## Current limitations

The project list/create/delete flow is implemented. AI agents and workflow execution are not implemented in the dashboard yet. Database migrations and production abuse protections are also pending.


## Conversations API

All endpoints require the same bearer authentication as projects.

- `GET /api/conversations` lists the signed-in user's conversations.
- `POST /api/conversations` creates a conversation with an optional title.
- `GET /api/conversations/{id}/messages` returns its message history.
- `POST /api/conversations/{id}/messages` sends a user message to the configured model and stores both user and assistant messages (up to 12,000 characters each).
- `DELETE /api/conversations/{id}` deletes the conversation and its messages.

Conversation ownership is checked on every operation. The backend supports OpenAI-compatible chat completions. Configure `AI_API_KEY` as a private Render environment variable; optionally set `AI_BASE_URL` and `AI_MODEL`. Defaults are the OpenAI API base URL and `gpt-4o-mini`. Do not place provider secrets in frontend variables or commit them. API usage may be billed separately; ChatGPT Free does not include API credits. Without a key, the endpoint returns HTTP 503 before storing the submitted message.
