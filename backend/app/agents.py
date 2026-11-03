from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from .auth import current_session
from .database import get_db
from .models import Agent, AgentTask, AgentTaskEvent, Session as LoginSession, User
from .ai_provider import is_configured, generate_reply

router = APIRouter(prefix="/api/agents", tags=["agents"])

class AgentInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    instructions: str = Field(default="", max_length=4000)
    model: str = Field(default="gpt-4o-mini", min_length=1, max_length=100)

class AgentUpdate(AgentInput):
    status: Literal["draft", "active", "paused"] = "draft"

def serialize(agent: Agent):
    return {
        "id": agent.id, "name": agent.name, "description": agent.description,
        "instructions": agent.instructions, "model": agent.model, "status": agent.status,
        "created": agent.created_at.isoformat(), "updated": agent.updated_at.isoformat()
    }

def owned_agent(agent_id: int, user_id: int, db: DBSession):
    agent = db.scalar(select(Agent).where(Agent.id == agent_id, Agent.owner_id == user_id))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("")
def list_agents(auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    rows = db.scalars(select(Agent).where(Agent.owner_id == auth[0].id).order_by(Agent.updated_at.desc())).all()
    return [serialize(row) for row in rows]

@router.get("/summary")
def agent_summary(auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    """Return aggregate counts for the authenticated user's workspace."""
    user_id = auth[0].id
    active_agents = db.scalar(select(func.count(Agent.id)).where(
        Agent.owner_id == user_id, Agent.status == "active"
    )) or 0
    successful_tasks = db.scalar(select(func.count(AgentTask.id)).where(
        AgentTask.owner_id == user_id, AgentTask.status == "succeeded"
    )) or 0
    return {"active_agents": active_agents, "successful_tasks": successful_tasks}

@router.post("", status_code=201)
def create_agent(data: AgentInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    name = data.name.strip()
    model = data.model.strip()
    if not name or not model:
        raise HTTPException(status_code=422, detail="Agent name and model are required")
    agent = Agent(owner_id=auth[0].id, name=name, description=data.description.strip(),
                  instructions=data.instructions.strip(), model=model, status="draft")
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return serialize(agent)

@router.put("/{agent_id}")
def update_agent(agent_id: int, data: AgentUpdate, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    agent = owned_agent(agent_id, auth[0].id, db)
    name = data.name.strip()
    model = data.model.strip()
    if not name or not model:
        raise HTTPException(status_code=422, detail="Agent name and model are required")
    agent.name = name
    agent.description = data.description.strip()
    agent.instructions = data.instructions.strip()
    agent.model = model
    agent.status = data.status
    agent.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agent)
    return serialize(agent)

@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    agent = owned_agent(agent_id, auth[0].id, db)
    db.delete(agent)
    db.commit()


class AgentRunInput(BaseModel):
    input: str = Field(min_length=1, max_length=8000)

def serialize_task(task: AgentTask):
    return {
        "id": task.id, "agent_id": task.agent_id, "input": task.input,
        "output": task.output, "status": task.status, "error": task.error,
        "created": task.created_at.isoformat(), "updated": task.updated_at.isoformat()
    }

@router.get("/{agent_id}/tasks")
def list_agent_tasks(agent_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    owned_agent(agent_id, auth[0].id, db)
    rows = db.scalars(select(AgentTask).where(
        AgentTask.agent_id == agent_id, AgentTask.owner_id == auth[0].id
    ).order_by(AgentTask.created_at.desc()).limit(50)).all()
    return [serialize_task(row) for row in rows]

@router.post("/{agent_id}/tasks", status_code=202)
def run_agent(agent_id: int, data: AgentRunInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    agent = owned_agent(agent_id, auth[0].id, db)
    prompt = data.input.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Task input is required")
    if agent.status != "active":
        raise HTTPException(status_code=409, detail="Agent must be active before it can run")
    if not is_configured():
        raise HTTPException(status_code=503, detail="AI provider is not configured")

    task = AgentTask(agent_id=agent.id, owner_id=auth[0].id, input=prompt, status="queued")
    db.add(task)
    db.flush()
    db.add(AgentTaskEvent(
        task_id=task.id,
        event_type="queued",
        detail="Task accepted and waiting for a background worker",
    ))
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.get("/{agent_id}/tasks/{task_id}")
def get_agent_task(agent_id: int, task_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    owned_agent(agent_id, auth[0].id, db)
    task = db.scalar(select(AgentTask).where(
        AgentTask.id == task_id, AgentTask.agent_id == agent_id, AgentTask.owner_id == auth[0].id
    ))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize_task(task)


@router.get("/{agent_id}/tasks/{task_id}/events")
def list_task_events(agent_id: int, task_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    owned_agent(agent_id, auth[0].id, db)
    task = db.scalar(select(AgentTask).where(
        AgentTask.id == task_id, AgentTask.agent_id == agent_id, AgentTask.owner_id == auth[0].id
    ))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    events = db.scalars(select(AgentTaskEvent).where(
        AgentTaskEvent.task_id == task.id
    ).order_by(AgentTaskEvent.created_at, AgentTaskEvent.id)).all()
    return [{"id": event.id, "type": event.event_type, "detail": event.detail,
             "created": event.created_at.isoformat()} for event in events]
