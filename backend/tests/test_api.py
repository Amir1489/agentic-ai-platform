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
