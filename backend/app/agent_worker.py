"""Lease-based database worker with stale-task recovery."""
import asyncio
import logging
import os
import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from .database import SessionLocal
from .models import Agent, AgentTask, AgentTaskEvent

logger = logging.getLogger(__name__)
LEASE_SECONDS = 90
HEARTBEAT_SECONDS = 15
MAX_ATTEMPTS = 3
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def utcnow():
    return datetime.now(timezone.utc)


def recover_expired_tasks():
    now = utcnow()
    with SessionLocal() as db:
        rows = db.scalars(select(AgentTask).where(
            AgentTask.status == "running",
            AgentTask.lease_expires_at.is_not(None),
            AgentTask.lease_expires_at < now,
        ).with_for_update(skip_locked=True)).all()
        for task in rows:
            previous_worker = task.worker_id or "unknown"
            if task.attempt_count >= MAX_ATTEMPTS:
                task.status = "failed"
                task.error = "Worker lease expired; maximum attempts reached"
                event_type = "failed"
            else:
                task.status = "queued"
                task.error = "Previous worker lease expired; task requeued"
                event_type = "recovered"
            task.worker_id = ""
            task.claimed_at = None
            task.heartbeat_at = None
            task.lease_expires_at = None
            task.updated_at = now
            db.add(AgentTaskEvent(task_id=task.id, event_type=event_type,
                                  detail=f"Expired lease from {previous_worker}; attempts={task.attempt_count}"))
        db.commit()
        return len(rows)


def claim_one():
    now = utcnow()
    with SessionLocal() as db:
        candidate = db.scalar(select(AgentTask.id).where(
            AgentTask.status == "queued"
        ).order_by(AgentTask.created_at, AgentTask.id).limit(1))
        if candidate is None:
            return None
        result = db.execute(update(AgentTask).where(
            AgentTask.id == candidate, AgentTask.status == "queued"
        ).values(
            status="running", worker_id=WORKER_ID, claimed_at=now,
            heartbeat_at=now, lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
            attempt_count=AgentTask.attempt_count + 1, updated_at=now,
        ))
        if result.rowcount != 1:
            db.rollback()
            return None
        task = db.get(AgentTask, candidate)
        if task is None:
            db.commit()
            return None
        agent = db.scalar(select(Agent).where(
            Agent.id == task.agent_id, Agent.owner_id == task.owner_id
        ))
        snapshot = {
            "id": task.id, "input": task.input,
            "active": agent is not None and agent.status == "active",
            "instructions": (agent.instructions.strip() if agent else ""),
            "description": (agent.description if agent else ""),
            "model": (agent.model if agent else ""),
        }
        if not snapshot["instructions"]:
            snapshot["instructions"] = "You are a helpful, safe, concise AI agent. Reply in the user's language."
        snapshot["instructions"] += "\n\nAgent description: " + snapshot["description"][:500]
        db.add(AgentTaskEvent(task_id=task.id, event_type="started",
                              detail=f"Claimed by {WORKER_ID}; attempt {task.attempt_count}"))
        db.commit()
        return snapshot


def heartbeat(task_id, stop):
    while not stop.wait(HEARTBEAT_SECONDS):
        now = utcnow()
        try:
            with SessionLocal() as db:
                result = db.execute(update(AgentTask).where(
                    AgentTask.id == task_id,
                    AgentTask.status == "running",
                    AgentTask.worker_id == WORKER_ID,
                ).values(heartbeat_at=now,
                         lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
                         updated_at=now))
                db.commit()
                if result.rowcount != 1:
                    return
        except Exception:
            logger.exception("Heartbeat failed for task %s", task_id)


def process_one_task():
    recover_expired_tasks()
    task = claim_one()
    if task is None:
        return False
    task_id = task["id"]
    if not task["active"]:
        finish(task_id, status="failed", error="Agent is unavailable or inactive")
        return True

    stop = threading.Event()
    pulse = threading.Thread(target=heartbeat, args=(task_id, stop), daemon=True)
    pulse.start()
    try:
        from . import agents as agent_api
        output = agent_api.generate_reply(
            [{"role": "user", "content": task["input"]}],
            system_prompt=task["instructions"], model=task["model"],
        )
        finish(task_id, status="succeeded", output=output[:12000])
    except Exception:
        logger.exception("Agent task %s failed", task_id)
        retry_or_fail(task_id)
    finally:
        stop.set()
        pulse.join(timeout=2)
    return True


def finish(task_id, status, output="", error=""):
    now = utcnow()
    with SessionLocal() as db:
        task = db.scalar(select(AgentTask).where(
            AgentTask.id == task_id, AgentTask.status == "running",
            AgentTask.worker_id == WORKER_ID,
        ))
        if task is None:
            return
        task.status = status
        task.output = output
        task.error = error
        task.worker_id = ""
        task.claimed_at = None
        task.heartbeat_at = None
        task.lease_expires_at = None
        task.updated_at = now
        db.add(AgentTaskEvent(task_id=task_id, event_type=status,
                              detail="Task completed by lease owner"))
        db.commit()


def retry_or_fail(task_id):
    now = utcnow()
    with SessionLocal() as db:
        task = db.scalar(select(AgentTask).where(
            AgentTask.id == task_id, AgentTask.status == "running",
            AgentTask.worker_id == WORKER_ID,
        ))
        if task is None:
            return
        if task.attempt_count < MAX_ATTEMPTS:
            task.status = "queued"
            task.error = "AI provider request failed; task queued for retry"
            event_type = "retry"
        else:
            task.status = "failed"
            task.error = "The AI provider request failed after maximum attempts"
            event_type = "failed"
        task.worker_id = ""
        task.claimed_at = None
        task.heartbeat_at = None
        task.lease_expires_at = None
        task.updated_at = now
        db.add(AgentTaskEvent(task_id=task_id, event_type=event_type,
                              detail=f"{task.error} (attempt {task.attempt_count})"))
        db.commit()


async def worker_loop(poll_interval: float = 1.0):
    while True:
        try:
            found = await asyncio.to_thread(process_one_task)
            if not found:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background worker iteration failed")
            await asyncio.sleep(poll_interval)
