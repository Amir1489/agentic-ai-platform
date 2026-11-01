import os
import tempfile
import time
from pathlib import Path

db_path = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from fastapi.testclient import TestClient
from app.main import app


def wait_for_task(client, url, headers, expected_status, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(url, headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] == expected_status:
            return task
        time.sleep(0.05)
    raise AssertionError(f"Task did not reach {expected_status} before timeout")

def test_health_and_account_isolation():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        capabilities = client.get("/api/capabilities")
        assert capabilities.status_code == 200
        assert set(capabilities.json()) == {"chat", "agent_tasks"}
        assert client.get("/api/ready").json() == {"status": "ready", "database": "reachable"}
        assert client.get("/api/projects").status_code == 401
        users = []
        for index in (1, 2):
            response = client.post("/api/auth/register", json={
                "email": f"tester{index}@example.com",
                "password": "secure-test-password-123"
            })
            assert response.status_code == 201, response.text
            users.append(response.json()["token"])
        login_ok = client.post("/api/auth/login", json={"email": "tester1@example.com", "password": "secure-test-password-123"})
        assert login_ok.status_code == 200
        login_token = login_ok.json()["token"]
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_token}"}).json()["email"] == "tester1@example.com"
        login_bad = client.post("/api/auth/login", json={"email": "tester1@example.com", "password": "incorrect-password-123"})
        assert login_bad.status_code == 401
        login_too_long = client.post("/api/auth/login", json={"email": "tester1@example.com", "password": "x" * 129})
        assert login_too_long.status_code == 422
        headers_a = {"Authorization": f"Bearer {users[0]}"}
        headers_b = {"Authorization": f"Bearer {users[1]}"}
        project = client.post("/api/projects", headers=headers_a, json={"name": "My project"})
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]
        assert len(client.get("/api/projects", headers=headers_a).json()) == 1
        assert client.get("/api/projects", headers=headers_b).json() == []
        assert client.delete(f"/api/projects/{project_id}", headers=headers_b).status_code == 404
        assert client.delete(f"/api/projects/{project_id}", headers=headers_a).status_code == 204
        assert client.get("/api/projects", headers=headers_a).json() == []
        assert client.post("/api/auth/logout", headers=headers_a).status_code == 204
        assert client.get("/api/projects", headers=headers_a).status_code == 401


def test_conversation_isolation_and_atomic_chat(monkeypatch):
    import app.conversations as conversations

    with TestClient(app) as client:
        tokens = []
        for index in (3, 4):
            response = client.post("/api/auth/register", json={
                "email": f"chat{index}@example.com",
                "password": "secure-test-password-123"
            })
            assert response.status_code == 201, response.text
            tokens.append(response.json()["token"])

        headers_a = {"Authorization": f"Bearer {tokens[0]}"}
        headers_b = {"Authorization": f"Bearer {tokens[1]}"}
        created = client.post("/api/conversations", headers=headers_a, json={"title": "New conversation"})
        assert created.status_code == 201, created.text
        conversation_id = created.json()["id"]

        assert client.get(f"/api/conversations/{conversation_id}/messages", headers=headers_b).status_code == 404
        assert client.delete(f"/api/conversations/{conversation_id}", headers=headers_b).status_code == 404

        monkeypatch.setattr(conversations, "is_configured", lambda: False)
        unavailable = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers_a,
            json={"content": "Hello"}
        )
        assert unavailable.status_code == 503
        assert client.get(f"/api/conversations/{conversation_id}/messages", headers=headers_a).json() == []

        monkeypatch.setattr(conversations, "is_configured", lambda: True)
        monkeypatch.setattr(conversations, "generate_reply", lambda messages: "Hello back")
        sent = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers_a,
            json={"content": "Hello"}
        )
        assert sent.status_code == 201, sent.text
        payload = sent.json()
        assert payload["user_message"]["content"] == "Hello"
        assert payload["assistant_message"]["content"] == "Hello back"

        rows = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers_a).json()
        assert [item["role"] for item in rows] == ["user", "assistant"]
        listing = client.get("/api/conversations", headers=headers_a).json()
        assert listing[0]["title"] == "Hello"
        assert listing[0]["message_count"] == 2


def test_agent_crud_and_owner_isolation():
    with TestClient(app) as client:
        tokens = []
        for index in (5, 6):
            response = client.post("/api/auth/register", json={
                "email": f"agent{index}@example.com",
                "password": "secure-test-password-123"
            })
            assert response.status_code == 201, response.text
            tokens.append(response.json()["token"])
        headers_a = {"Authorization": f"Bearer {tokens[0]}"}
        headers_b = {"Authorization": f"Bearer {tokens[1]}"}
        payload = {
            "name": "Research helper",
            "description": "Summarizes supplied research",
            "instructions": "Be accurate and cite uncertainty.",
            "model": "gpt-4o-mini"
        }
        invalid_model = client.post("/api/agents", headers=headers_a, json={**payload, "model": "   "})
        assert invalid_model.status_code == 422
        created = client.post("/api/agents", headers=headers_a, json=payload)
        assert created.status_code == 201, created.text
        agent_id = created.json()["id"]
        assert created.json()["status"] == "draft"
        assert client.get("/api/agents", headers=headers_b).json() == []
        assert client.put(f"/api/agents/{agent_id}", headers=headers_b, json={**payload, "status": "active"}).status_code == 404
        updated = client.put(f"/api/agents/{agent_id}", headers=headers_a, json={**payload, "name": "Updated helper", "status": "active"})
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == "Updated helper"
        assert updated.json()["status"] == "active"
        assert client.delete(f"/api/agents/{agent_id}", headers=headers_b).status_code == 404
        assert client.delete(f"/api/agents/{agent_id}", headers=headers_a).status_code == 204
        assert client.get("/api/agents", headers=headers_a).json() == []


def test_agent_task_execution_requires_active_agent_and_persists_result(monkeypatch):
    import app.agents as agents

    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json={
            "email": "agent-runner@example.com",
            "password": "secure-test-password-123"
        })
        assert registered.status_code == 201
        headers = {"Authorization": "Bearer " + registered.json()["token"]}
        created = client.post("/api/agents", headers=headers, json={
            "name": "Study helper", "description": "Helps explain topics",
            "instructions": "Explain clearly.", "model": "gpt-4o-mini"
        })
        agent_id = created.json()["id"]
        monkeypatch.setattr(agents, "is_configured", lambda: True)
        blocked = client.post(f"/api/agents/{agent_id}/tasks", headers=headers, json={"input": "Explain fractions"})
        assert blocked.status_code == 409
        activated = client.put(f"/api/agents/{agent_id}", headers=headers, json={
            "name": "Study helper", "description": "Helps explain topics",
            "instructions": "Explain clearly.", "model": "gpt-4o-mini", "status": "active"
        })
        assert activated.status_code == 200
        seen = {}
        def fake_reply(messages, system_prompt=None, model=None):
            seen["model"] = model
            seen["system_prompt"] = system_prompt
            return "Fractions represent parts of a whole."
        monkeypatch.setattr(agents, "generate_reply", fake_reply)
        result = client.post(f"/api/agents/{agent_id}/tasks", headers=headers, json={"input": "Explain fractions"})
        assert result.status_code == 202, result.text
        queued = result.json()
        assert queued["status"] == "queued"
        task = wait_for_task(
            client,
            f"/api/agents/{agent_id}/tasks/{queued['id']}",
            headers,
            "succeeded",
        )
        assert task["output"].startswith("Fractions represent")
        assert seen["model"] == "gpt-4o-mini"
        assert "Explain clearly." in seen["system_prompt"]
        history = client.get(f"/api/agents/{agent_id}/tasks", headers=headers)
        assert history.status_code == 200
        assert history.json()[0]["id"] == task["id"]
        events = client.get(f"/api/agents/{agent_id}/tasks/{task['id']}/events", headers=headers)
        assert events.status_code == 200
        assert [event["type"] for event in events.json()] == ["queued", "started", "succeeded"]


def test_agent_provider_failure_is_recorded(monkeypatch):
    import app.agents as agents
    import app.agent_worker as worker
    from app.ai_provider import AIProviderError

    # Keep this integration test fast while exercising all bounded retry attempts.
    monkeypatch.setattr(worker, "retry_delay_seconds", lambda attempt: 0.01)

    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json={
            "email": "agent-failure@example.com",
            "password": "secure-test-password-123"
        })
        headers = {"Authorization": "Bearer " + registered.json()["token"]}
        created = client.post("/api/agents", headers=headers, json={
            "name": "Fallback agent", "description": "", "instructions": "",
            "model": "gpt-4o-mini"
        })
        agent_id = created.json()["id"]
        client.put(f"/api/agents/{agent_id}", headers=headers, json={
            "name": "Fallback agent", "description": "", "instructions": "",
            "model": "gpt-4o-mini", "status": "active"
        })
        monkeypatch.setattr(agents, "is_configured", lambda: True)
        def fail_provider(messages, system_prompt=None, model=None):
            raise AIProviderError("provider unavailable")
        monkeypatch.setattr(agents, "generate_reply", fail_provider)
        failed = client.post(f"/api/agents/{agent_id}/tasks", headers=headers, json={"input": "Run this"})
        assert failed.status_code == 202, failed.text
        queued = failed.json()
        assert queued["status"] == "queued"
        task = wait_for_task(
            client,
            f"/api/agents/{created.json()['id']}/tasks/{queued['id']}",
            headers,
            "failed",
        )
        assert task["status"] == "failed"
        history = client.get(f"/api/agents/{created.json()['id']}/tasks", headers=headers).json()
        assert history[0]["status"] == "failed"
        events = client.get(f"/api/agents/{agent_id}/tasks/{history[0]['id']}/events", headers=headers).json()
        assert [event["type"] for event in events] == ["queued", "started", "retry_scheduled", "started", "retry_scheduled", "started", "failed"]


def test_expired_session_is_rejected_and_removed():
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.auth import digest
    from app.database import SessionLocal
    from app.models import Session as LoginSession

    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json={
            "email": "expired-session@example.com",
            "password": "secure-test-password-123"
        })
        token = registered.json()["token"]
        with SessionLocal() as db:
            session = db.scalar(select(LoginSession).where(LoginSession.token_hash == digest(token)))
            assert session is not None
            session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 401
        with SessionLocal() as db:
            assert db.scalar(select(LoginSession).where(LoginSession.token_hash == digest(token))) is None


def test_cors_preflight_allows_agent_update():
    with TestClient(app) as client:
        response = client.options(
            "/api/agents/1",
            headers={
                "Origin": "https://amir1489.github.io",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200, response.text
        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "PUT" in allowed_methods
        assert response.headers.get("access-control-allow-origin") == "https://amir1489.github.io"
