"""PostgreSQL integration tests for agent task claim and restart recovery.

Run separately from the SQLite unit suite with DATABASE_URL pointing at a
disposable PostgreSQL database whose schema has been migrated with Alembic.
"""
from concurrent.futures import ThreadPoolExecutor
import pytest
from datetime import datetime, timedelta, timezone
from threading import Barrier
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models import Agent, AgentTask, AgentTaskEvent, User
from app import agent_worker

# These tests require PostgreSQL row-locking semantics and run in a dedicated CI step.
pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="PostgreSQL integration tests run only against the dedicated PostgreSQL service",
)


def test_concurrent_workers_only_claim_a_task_once():
    suffix = uuid4().hex
    with SessionLocal() as db:
        user = User(email=f"pg-lease-{suffix}@example.com", password_hash="test-hash")
        db.add(user)
        db.flush()
        agent = Agent(
            owner_id=user.id,
            name="PostgreSQL concurrency agent",
            description="",
            instructions="Be concise",
            model="gpt-4o-mini",
            status="active",
        )
        db.add(agent)
        db.flush()
        task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            input="Concurrent claim test",
            status="queued",
        )
        db.add(task)
        db.commit()
        task_id = task.id

    workers = 8
    barrier = Barrier(workers)

    def attempt_claim():
        barrier.wait(timeout=10)
        return agent_worker.claim_one()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: attempt_claim(), range(workers)))

    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert winners[0]["id"] == task_id

    with SessionLocal() as db:
        claimed = db.scalar(select(AgentTask).where(AgentTask.id == task_id))
        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.worker_id == agent_worker.WORKER_ID
        assert claimed.attempt_count == 1

        # Leave no running lease behind for the next integration test.
        claimed.status = "succeeded"
        claimed.worker_id = ""
        claimed.claimed_at = None
        claimed.heartbeat_at = None
        claimed.lease_expires_at = None
        db.commit()


def test_fresh_process_recovers_tasks_left_by_previous_worker():
    """A new process recovers persisted leases without relying on old memory."""
    suffix = uuid4().hex
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        user = User(email=f"pg-restart-{suffix}@example.com", password_hash="test-hash")
        db.add(user)
        db.flush()
        agent = Agent(
            owner_id=user.id,
            name="PostgreSQL restart recovery agent",
            description="",
            instructions="Be concise",
            model="gpt-4o-mini",
            status="active",
        )
        db.add(agent)
        db.flush()

        retry_task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            input="Recover after process restart",
            status="running",
            worker_id="crashed-worker-retry",
            claimed_at=now - timedelta(minutes=3),
            heartbeat_at=now - timedelta(minutes=2),
            lease_expires_at=now - timedelta(seconds=30),
            attempt_count=1,
        )
        exhausted_task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            input="Fail after attempt limit",
            status="running",
            worker_id="crashed-worker-exhausted",
            claimed_at=now - timedelta(minutes=3),
            heartbeat_at=now - timedelta(minutes=2),
            lease_expires_at=now - timedelta(seconds=30),
            attempt_count=agent_worker.MAX_ATTEMPTS,
        )
        active_task = AgentTask(
            agent_id=agent.id,
            owner_id=user.id,
            input="Do not recover a live lease",
            status="running",
            worker_id="still-active-worker",
            claimed_at=now,
            heartbeat_at=now,
            lease_expires_at=now + timedelta(minutes=2),
            attempt_count=1,
        )
        db.add_all([retry_task, exhausted_task, active_task])
        db.commit()
        retry_id = retry_task.id
        exhausted_id = exhausted_task.id
        active_id = active_task.id

    # A separate interpreter gets a fresh process identity and a new DB session.
    script = (
        "from app.agent_worker import WORKER_ID, recover_expired_tasks\n"
        "print(f'{WORKER_ID}|{recover_expired_tasks()}')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, (
        "Fresh worker process failed during recovery: " + completed.stderr
    )
    new_worker_id, recovered_count = completed.stdout.strip().split("|", 1)

    assert new_worker_id
    assert new_worker_id not in {
        "crashed-worker-retry",
        "crashed-worker-exhausted",
        "still-active-worker",
    }
    assert int(recovered_count) == 2

    with SessionLocal() as db:
        retry = db.get(AgentTask, retry_id)
        exhausted = db.get(AgentTask, exhausted_id)
        active = db.get(AgentTask, active_id)

        assert retry.status == "queued"
        assert retry.worker_id == ""
        assert retry.lease_expires_at is None
        assert retry.attempt_count == 1

        assert exhausted.status == "failed"
        assert exhausted.worker_id == ""
        assert exhausted.lease_expires_at is None
        assert "maximum attempts" in exhausted.error

        assert active.status == "running"
        assert active.worker_id == "still-active-worker"
        assert active.lease_expires_at > now

        retry_events = db.scalars(
            select(AgentTaskEvent).where(AgentTaskEvent.task_id == retry_id)
        ).all()
        exhausted_events = db.scalars(
            select(AgentTaskEvent).where(AgentTaskEvent.task_id == exhausted_id)
        ).all()
        active_events = db.scalars(
            select(AgentTaskEvent).where(AgentTaskEvent.task_id == active_id)
        ).all()

        assert [event.event_type for event in retry_events] == ["recovered"]
        assert [event.event_type for event in exhausted_events] == ["failed"]
        assert active_events == []
