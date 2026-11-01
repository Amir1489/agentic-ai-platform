"""PostgreSQL integration tests for concurrent agent task claims.

Run separately from the SQLite unit suite with DATABASE_URL pointing at a
disposable PostgreSQL database whose schema has been migrated with Alembic.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Agent, AgentTask, User
from app import agent_worker


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
