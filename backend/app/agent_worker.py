"""Database-backed worker for queued agent tasks.

Multiple API processes may poll the same queue. A conditional status update
claims each task atomically so only one process executes it.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from .database import SessionLocal
from .models import Agent, AgentTask, AgentTaskEvent

logger = logging.getLogger(__name__)


def process_one_task() -> bool:
    """Claim and execute at most one queued task. Returns whether work was found."""
    with SessionLocal() as db:
        candidate_id = db.scalar(
            select(AgentTask.id)
            .where(AgentTask.status == "queued")
            .order_by(AgentTask.created_at, AgentTask.id)
            .limit(1)
        )
        if candidate_id is None:
            return False

        now = datetime.now(timezone.utc)
        claimed = db.execute(
            update(AgentTask)
            .where(AgentTask.id == candidate_id, AgentTask.status == "queued")
            .values(status="running", updated_at=now)
        )
        if claimed.rowcount != 1:
            db.rollback()
            return True

        task = db.get(AgentTask, candidate_id)
        if task is None:
            db.commit()
            return True
        agent = db.scalar(
            select(Agent).where(Agent.id == task.agent_id, Agent.owner_id == task.owner_id)
        )
        db.add(AgentTaskEvent(
            task_id=task.id,
            event_type="started",
            detail="Task claimed by background worker",
        ))
        db.commit()

        if agent is None or agent.status != "active":
            task.status = "failed"
            task.error = "Agent is unavailable or inactive"
            task.updated_at = datetime.now(timezone.utc)
            db.add(AgentTaskEvent(task_id=task.id, event_type="failed", detail=task.error))
            db.commit()
            return True

        task_id = task.id
        prompt = task.input
        system_prompt = agent.instructions.strip() or (
            "You are a helpful, safe, concise AI agent. Reply in the user's language."
        )
        system_prompt += "\\n\\nAgent description: " + agent.description[:500]
        model = agent.model

        try:
            # Keep the database transaction closed while waiting on the provider.
            from . import agents as agent_api
            output = agent_api.generate_reply(
                [{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                model=model,
            )
            task = db.get(AgentTask, task_id)
            if task is not None and task.status == "running":
                task.output = output[:12000]
                task.status = "succeeded"
                task.error = ""
                task.updated_at = datetime.now(timezone.utc)
                db.add(AgentTaskEvent(
                    task_id=task.id,
                    event_type="succeeded",
                    detail="Model response stored by background worker",
                ))
                db.commit()
        except Exception:
            logger.exception("Agent task %s failed during provider execution", task_id)
            db.rollback()
            task = db.get(AgentTask, task_id)
            if task is not None and task.status == "running":
                task.status = "failed"
                task.error = "The AI provider request failed"
                task.updated_at = datetime.now(timezone.utc)
                db.add(AgentTaskEvent(task_id=task.id, event_type="failed", detail=task.error))
                db.commit()
        return True


async def worker_loop(poll_interval: float = 1.0) -> None:
    """Poll the durable database queue until the application shuts down."""
    while True:
        try:
            found_work = await asyncio.to_thread(process_one_task)
            if not found_work:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background task worker iteration failed")
            await asyncio.sleep(poll_interval)
