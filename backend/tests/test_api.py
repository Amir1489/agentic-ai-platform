import os
import tempfile
from pathlib import Path

db_path = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from fastapi.testclient import TestClient
from app.main import app

def test_health_and_account_isolation():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
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
        monkeypatch.setattr(agents, "generate_reply", lambda messages, system_prompt=None: "Fractions represent parts of a whole.")
        result = client.post(f"/api/agents/{agent_id}/tasks", headers=headers, json={"input": "Explain fractions"})
        assert result.status_code == 201, result.text
        task = result.json()
        assert task["status"] == "succeeded"
        assert task["output"].startswith("Fractions represent")
        history = client.get(f"/api/agents/{agent_id}/tasks", headers=headers)
        assert history.status_code == 200
        assert history.json()[0]["id"] == task["id"]
