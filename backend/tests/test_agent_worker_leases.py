import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import threading
import time

# This module may be collected before test_api.py, so configure the test DB
# before importing the application database module.
db_path = Path(tempfile.mkdtemp()) / "lease-tests.db"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from sqlalchemy import select
from app.database import Base, SessionLocal, engine
from app.models import Agent, AgentTask, AgentTaskEvent, User
from app import agent_worker
from fastapi.testclient import TestClient
from app.main import app

# Reuse the application lifespan so schema creation matches production startup.
with TestClient(app):
    pass


def make_task(attempt_count=0, status="running", lease_expired=True):
    suffix = uuid4().hex
    with SessionLocal() as db:
        user = User(email=f"lease-{suffix}@example.com", password_hash="test-hash")
        db.add(user)
        db.flush()
        agent = Agent(
            owner_id=user.id, name="Lease test agent", description="",
            instructions="Be concise", model="gpt-4o-mini", status="active",
        )
        db.add(agent)
        db.flush()
        now = datetime.now(timezone.utc)
        task = AgentTask(
            agent_id=agent.id, owner_id=user.id, input="Test task",
            status=status, attempt_count=attempt_count,
            worker_id="dead-worker" if status == "running" else "",
            claimed_at=now - timedelta(minutes=5) if status == "running" else None,
            heartbeat_at=now - timedelta(minutes=5) if status == "running" else None,
            lease_expires_at=(
                now - timedelta(minutes=1)
                if status == "running" and lease_expired
                else now + timedelta(minutes=2) if status == "running" else None
            ),
        )
        db.add(task)
        db.commit()
        return task.id


def test_expired_lease_is_requeued_and_audited():
    task_id = make_task(attempt_count=1)
    assert agent_worker.recover_expired_tasks() >= 1
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "queued"
        assert task.worker_id == ""
        assert task.lease_expires_at is None
        events = db.scalars(select(AgentTaskEvent).where(AgentTaskEvent.task_id == task_id)).all()
        assert any(event.event_type == "recovered" for event in events)
        task.status = "failed"
        db.commit()


def test_expired_lease_at_attempt_limit_fails():
    task_id = make_task(attempt_count=agent_worker.MAX_ATTEMPTS)
    agent_worker.recover_expired_tasks()
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "failed"
        assert "maximum attempts" in task.error
        events = db.scalars(select(AgentTaskEvent).where(AgentTaskEvent.task_id == task_id)).all()
        assert any(event.event_type == "failed" for event in events)


def test_claim_is_single_winner_and_increments_attempt():
    task_id = make_task(status="queued", lease_expired=False)
    first = agent_worker.claim_one()
    assert first is not None and first["id"] == task_id
    assert agent_worker.claim_one() is None
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "running"
        assert task.worker_id == agent_worker.WORKER_ID
        assert task.attempt_count == 1
        assert task.lease_expires_at is not None


def test_heartbeat_extends_lease_for_current_owner(monkeypatch):
    task_id = make_task(status="queued", lease_expired=False)
    claimed = agent_worker.claim_one()
    assert claimed is not None and claimed["id"] == task_id
    with SessionLocal() as db:
        original_expiry = db.get(AgentTask, task_id).lease_expires_at
    monkeypatch.setattr(agent_worker, "HEARTBEAT_SECONDS", 0.01)
    stop = threading.Event()
    pulse = threading.Thread(target=agent_worker.heartbeat, args=(task_id, claimed["lease_token"], stop), daemon=True)
    pulse.start()
    time.sleep(0.04)
    stop.set()
    pulse.join(timeout=1)
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.lease_expires_at > original_expiry
        assert task.worker_id == agent_worker.WORKER_ID


def test_stale_worker_cannot_extend_lease(monkeypatch):
    task_id = make_task(status="queued", lease_expired=False)
    claimed = agent_worker.claim_one()
    assert claimed is not None and claimed["id"] == task_id
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        old_heartbeat = task.heartbeat_at
        task.worker_id = "replacement-worker"
        task.lease_token = "replacement-token"
        db.commit()

    monkeypatch.setattr(agent_worker, "HEARTBEAT_SECONDS", 0.01)
    stop = threading.Event()
    pulse = threading.Thread(target=agent_worker.heartbeat, args=(task_id, claimed["lease_token"], stop), daemon=True)
    pulse.start()
    pulse.join(timeout=1)
    assert not pulse.is_alive()
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.worker_id == "replacement-worker"
        assert task.heartbeat_at == old_heartbeat


def test_stale_worker_cannot_finish_reclaimed_task():
    task_id = make_task(status="queued", lease_expired=False)
    claimed = agent_worker.claim_one()
    assert claimed is not None and claimed["id"] == task_id
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        task.worker_id = "replacement-worker"
        db.commit()

    agent_worker.finish(task_id, claimed["lease_token"], status="succeeded", output="stale result")
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "running"
        assert task.worker_id == "replacement-worker"
        assert task.output != "stale result"



def test_retry_delay_is_exponential_and_capped():
    assert agent_worker.retry_delay_seconds(1, jitter=False) == 5
    assert agent_worker.retry_delay_seconds(2, jitter=False) == 10
    assert agent_worker.retry_delay_seconds(3, jitter=False) == 20
    assert agent_worker.retry_delay_seconds(10, jitter=False) == 60
    assert agent_worker.retry_delay_seconds(10, jitter=True) <= 60


def test_retry_is_scheduled_and_not_claimable_early(monkeypatch):
    task_id = make_task(status="queued", lease_expired=False)
    claimed = agent_worker.claim_one()
    assert claimed is not None and claimed["id"] == task_id
    monkeypatch.setattr(agent_worker, "retry_delay_seconds", lambda attempt: 30)
    assert agent_worker.retry_or_fail(task_id, claimed["lease_token"], retryable=True)
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "queued"
        assert task.next_retry_at is not None
        assert task.next_retry_at > datetime.now(timezone.utc)
        assert task.worker_id == ""
        assert task.lease_token == ""
    assert agent_worker.claim_one() is None


def test_non_retryable_error_fails_without_requeue():
    task_id = make_task(status="queued", lease_expired=False)
    claimed = agent_worker.claim_one()
    assert claimed is not None and claimed["id"] == task_id
    assert agent_worker.retry_or_fail(task_id, claimed["lease_token"], retryable=False)
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "failed"
        assert task.next_retry_at is None


def test_stale_lease_token_cannot_finish_or_retry():
    task_id = make_task(status="queued", lease_expired=False)
    claimed = agent_worker.claim_one()
    assert claimed is not None and claimed["id"] == task_id
    assert not agent_worker.finish(task_id, "stale-token", status="succeeded", output="stale")
    assert not agent_worker.retry_or_fail(task_id, "stale-token")
    with SessionLocal() as db:
        task = db.get(AgentTask, task_id)
        assert task.status == "running"
        assert task.lease_token == claimed["lease_token"]
