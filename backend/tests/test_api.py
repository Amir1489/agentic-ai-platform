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
        assert client.get("/api/agents/summary", headers=headers_a).json() == {"active_agents": 0, "successful_tasks": 0}
        assert client.get("/api/agents/summary", headers=headers_b).json() == {"active_agents": 0, "successful_tasks": 0}
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
        summary = client.get("/api/agents/summary", headers=headers).json()
        assert summary == {"active_agents": 1, "successful_tasks": 1}
        events = client.get(f"/api/agents/{agent_id}/tasks/{task['id']}/events", headers=headers)
        assert events.status_code == 200
        assert [event["type"] for event in events.json()] == ["queued", "started", "succeeded"]


def test_agent_provider_failure_is_recorded(monkeypatch):
    import app.agents as agents
    from app.ai_provider import AIProviderError

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
        assert [event["type"] for event in events] == ["queued", "started", "failed"]


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



def test_agent_task_endpoints_enforce_authentication_and_owner_isolation():
    from app.database import SessionLocal
    from app.models import Agent, AgentTask, AgentTaskEvent

    with TestClient(app) as client:
        registered_a = client.post("/api/auth/register", json={
            "email": "task-owner-a@example.com",
            "password": "secure-test-password-123"
        })
        registered_b = client.post("/api/auth/register", json={
            "email": "task-owner-b@example.com",
            "password": "secure-test-password-123"
        })
        assert registered_a.status_code == 201
        assert registered_b.status_code == 201
        headers_a = {"Authorization": "Bearer " + registered_a.json()["token"]}
        headers_b = {"Authorization": "Bearer " + registered_b.json()["token"]}

        created = client.post("/api/agents", headers=headers_a, json={
            "name": "Private task agent",
            "description": "Owner-scoped test agent",
            "instructions": "Test only",
            "model": "gpt-4o-mini",
        })
        assert created.status_code == 201
        agent_id = created.json()["id"]

        with SessionLocal() as db:
            task = AgentTask(
                agent_id=agent_id,
                owner_id=registered_a.json()["user"]["id"],
                input="private task input",
                output="private task output",
                status="succeeded",
            )
            db.add(task)
            db.flush()
            task_id = task.id
            db.add(AgentTaskEvent(
                task_id=task_id,
                event_type="succeeded",
                detail="private event detail",
            ))
            db.commit()

        task_url = f"/api/agents/{agent_id}/tasks/{task_id}"
        events_url = task_url + "/events"
        assert client.get(f"/api/agents/{agent_id}/tasks").status_code == 401
        assert client.get(task_url).status_code == 401
        assert client.get(events_url).status_code == 401

        assert client.get(f"/api/agents/{agent_id}/tasks", headers=headers_b).status_code == 404
        assert client.get(task_url, headers=headers_b).status_code == 404
        assert client.get(events_url, headers=headers_b).status_code == 404

        own_task = client.get(task_url, headers=headers_a)
        assert own_task.status_code == 200
        assert own_task.json()["input"] == "private task input"
        own_events = client.get(events_url, headers=headers_a)
        assert own_events.status_code == 200
        assert [event["type"] for event in own_events.json()] == ["succeeded"]


def test_registration_rate_limit_is_shared_and_returns_retry_after(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "REGISTER_LIMIT", 1)
    monkeypatch.setattr(main, "REGISTER_WINDOW_SECONDS", 3600)
    with TestClient(app, client=("203.0.113.40", 51001)) as client:
        first = client.post("/api/auth/register", json={
            "email": "rate-register-a@example.com",
            "password": "secure-test-password-123",
        })
        assert first.status_code == 201, first.text
        blocked = client.post("/api/auth/register", json={
            "email": "rate-register-b@example.com",
            "password": "secure-test-password-123",
        })
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0


def test_login_rate_limit_is_scoped_to_account_and_client(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "LOGIN_LIMIT", 2)
    monkeypatch.setattr(main, "LOGIN_WINDOW_SECONDS", 900)
    with TestClient(app, client=("203.0.113.41", 51002)) as client:
        registered = client.post("/api/auth/register", json={
            "email": "rate-login@example.com",
            "password": "secure-test-password-123",
        })
        assert registered.status_code == 201, registered.text

        payload = {"email": "rate-login@example.com", "password": "incorrect-password-123"}
        assert client.post("/api/auth/login", json=payload).status_code == 401
        assert client.post("/api/auth/login", json=payload).status_code == 401
        blocked = client.post("/api/auth/login", json=payload)
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0



def test_rate_limit_prunes_expired_buckets():
    from app.database import SessionLocal
    from app.models import AuthRateLimitBucket
    from app.rate_limit import enforce_auth_rate_limit, REGISTER_LIMIT, REGISTER_WINDOW_SECONDS
    from starlette.requests import Request

    with TestClient(app):
        with SessionLocal() as db:
            db.add(AuthRateLimitBucket(
                bucket_key="f" * 64,
                window_start=int(time.time()) - 3 * REGISTER_WINDOW_SECONDS,
                request_count=99,
            ))
            db.commit()

        request = Request({
            "type": "http", "http_version": "1.1", "method": "POST",
            "scheme": "http", "path": "/api/auth/register",
            "raw_path": b"/api/auth/register", "query_string": b"",
            "headers": [], "client": ("203.0.113.42", 51003),
            "server": ("testserver", 80),
        })
        with SessionLocal() as db:
            enforce_auth_rate_limit(
                db, request, scope="register", identity="",
                limit=REGISTER_LIMIT, window_seconds=REGISTER_WINDOW_SECONDS,
            )
        with SessionLocal() as db:
            assert db.get(AuthRateLimitBucket, "f" * 64) is None



def test_rate_limit_counter_is_shared_across_independent_sessions():
    import hashlib
    from app.database import SessionLocal
    from app.models import AuthRateLimitBucket
    from app.rate_limit import enforce_auth_rate_limit
    from starlette.requests import Request

    identity = f"multi-session-{time.time_ns()}"
    request = Request({
        "type": "http", "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": "/api/auth/login",
        "raw_path": b"/api/auth/login", "query_string": b"",
        "headers": [], "client": ("203.0.113.77", 51004),
        "server": ("testserver", 80),
    })
    for _ in range(2):
        with SessionLocal() as db:
            enforce_auth_rate_limit(
                db, request, scope="session-test", identity=identity,
                limit=10, window_seconds=900,
            )

    key = hashlib.sha256(
        f"session-test:203.0.113.77:{identity}".encode("utf-8")
    ).hexdigest()
    with SessionLocal() as verification_db:
        bucket = verification_db.get(AuthRateLimitBucket, key)
        assert bucket is not None
        assert bucket.request_count == 2
