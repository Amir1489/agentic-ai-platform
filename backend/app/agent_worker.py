"""Lease-based database worker with bounded exponential retry backoff."""
import asyncio
import logging
import os
import random
import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update

from .database import SessionLocal
from .models import Agent, AgentTask, AgentTaskEvent
from .ai_provider import AIProviderError, AIProviderNotConfigured

logger = logging.getLogger(__name__)
LEASE_SECONDS = 90
HEARTBEAT_SECONDS = 15
MAX_ATTEMPTS = 3
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 60
RETRY_JITTER_RATIO = 0.20
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def utcnow():
    return datetime.now(timezone.utc)


def retry_delay_seconds(attempt_count: int, *, jitter: bool = True) -> float:
    """Return capped exponential delay after a failed attempt (1-based)."""
    attempt = max(1, int(attempt_count))
    delay = min(RETRY_BASE_SECONDS * (2 ** (attempt - 1)), RETRY_MAX_SECONDS)
    if jitter:
        delay = min(delay * random.uniform(1 - RETRY_JITTER_RATIO, 1 + RETRY_JITTER_RATIO), RETRY_MAX_SECONDS)
    return delay


def clear_lease(task):
    task.worker_id = ""
    task.lease_token = ""
    task.claimed_at = None
    task.heartbeat_at = None
    task.lease_expires_at = None


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
                task.next_retry_at = None
                event_type = "failed"
            else:
                task.status = "queued"
                task.error = "Previous worker lease expired; task requeued"
                task.next_retry_at = now + timedelta(
                    seconds=retry_delay_seconds(task.attempt_count)
                )
                event_type = "recovered"
            clear_lease(task)
            task.updated_at = now
            db.add(AgentTaskEvent(
                task_id=task.id, event_type=event_type,
                detail=f"Expired lease from {previous_worker}; attempts={task.attempt_count}",
            ))
        db.commit()
        return len(rows)


def claim_one():
    now = utcnow()
    with SessionLocal() as db:
        candidate = db.scalar(select(AgentTask.id).where(
            AgentTask.status == "queued",
            or_(AgentTask.next_retry_at.is_(None), AgentTask.next_retry_at <= now),
        ).order_by(AgentTask.created_at, AgentTask.id).limit(1))
        if candidate is None:
            return None
        lease_token = str(uuid.uuid4())
        result = db.execute(update(AgentTask).where(
            AgentTask.id == candidate,
            AgentTask.status == "queued",
            or_(AgentTask.next_retry_at.is_(None), AgentTask.next_retry_at <= now),
        ).values(
            status="running", worker_id=WORKER_ID, lease_token=lease_token,
            claimed_at=now, heartbeat_at=now,
            lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
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
            "id": task.id, "input": task.input, "lease_token": lease_token,
            "active": agent is not None and agent.status == "active",
            "instructions": (agent.instructions.strip() if agent else ""),
            "description": (agent.description if agent else ""),
            "model": (agent.model if agent else ""),
        }
        if not snapshot["instructions"]:
            snapshot["instructions"] = "You are a helpful, safe, concise AI agent. Reply in the user's language."
        snapshot["instructions"] += "\n\nAgent description: " + snapshot["description"][:500]
        db.add(AgentTaskEvent(
            task_id=task.id, event_type="started",
            detail=f"Claimed by {WORKER_ID}; attempt {task.attempt_count}",
        ))
        db.commit()
        return snapshot


def heartbeat(task_id, lease_token, stop):
    while not stop.wait(HEARTBEAT_SECONDS):
        now = utcnow()
        try:
            with SessionLocal() as db:
                result = db.execute(update(AgentTask).where(
                    AgentTask.id == task_id, AgentTask.status == "running",
                    AgentTask.worker_id == WORKER_ID,
                    AgentTask.lease_token == lease_token,
                ).values(
                    heartbeat_at=now,
                    lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
                    updated_at=now,
                ))
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
    task_id, lease_token = task["id"], task["lease_token"]
    if not task["active"]:
        finish(task_id, lease_token, status="failed",
               error="Agent is unavailable or inactive")
        return True

    stop = threading.Event()
    pulse = threading.Thread(
        target=heartbeat, args=(task_id, lease_token, stop), daemon=True
    )
    pulse.start()
    try:
        from . import agents as agent_api
        output = agent_api.generate_reply(
            [{"role": "user", "content": task["input"]}],
            system_prompt=task["instructions"], model=task["model"],
        )
        finish(task_id, lease_token, status="succeeded", output=output[:12000])
    except AIProviderNotConfigured:
        logger.exception("AI provider is not configured for task %s", task_id)
        finish(task_id, lease_token, status="failed",
               error="AI provider is not configured")
    except AIProviderError as exc:
        logger.warning("AI provider request failed for task %s", task_id)
        retry_or_fail(task_id, lease_token, retryable=exc.retryable)
    except Exception:
        logger.exception("Unexpected agent task failure %s", task_id)
        retry_or_fail(task_id, lease_token, retryable=False)
    finally:
        stop.set()
        pulse.join(timeout=2)
    return True


def finish(task_id, lease_token, status, output="", error=""):
    now = utcnow()
    with SessionLocal() as db:
        task = db.scalar(select(AgentTask).where(
            AgentTask.id == task_id, AgentTask.status == "running",
            AgentTask.worker_id == WORKER_ID,
            AgentTask.lease_token == lease_token,
        ))
        if task is None:
            return False
        task.status = status
        task.output = output
        task.error = error
        task.next_retry_at = None
        clear_lease(task)
        task.updated_at = now
        db.add(AgentTaskEvent(
            task_id=task_id, event_type=status,
            detail="Task completed by current lease owner",
        ))
        db.commit()
        return True


def retry_or_fail(task_id, lease_token, *, retryable=True):
    now = utcnow()
    with SessionLocal() as db:
        task = db.scalar(select(AgentTask).where(
            AgentTask.id == task_id, AgentTask.status == "running",
            AgentTask.worker_id == WORKER_ID,
            AgentTask.lease_token == lease_token,
        ))
        if task is None:
            return False
        if retryable and task.attempt_count < MAX_ATTEMPTS:
            delay = retry_delay_seconds(task.attempt_count)
            task.status = "queued"
            task.error = "AI provider request failed; retry scheduled"
            task.next_retry_at = now + timedelta(seconds=delay)
            event_type = "retry_scheduled"
            detail = f"Retry scheduled after {delay:.1f}s (attempt {task.attempt_count}/{MAX_ATTEMPTS})"
        else:
            task.status = "failed"
            task.error = (
                "AI provider request failed after maximum attempts"
                if retryable else "AI provider request failed with a non-retryable error"
            )
            task.next_retry_at = None
            event_type = "failed"
            detail = f"{task.error} (attempt {task.attempt_count}/{MAX_ATTEMPTS})"
        clear_lease(task)
        task.updated_at = now
        db.add(AgentTaskEvent(task_id=task_id, event_type=event_type, detail=detail))
        db.commit()
        return True


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
