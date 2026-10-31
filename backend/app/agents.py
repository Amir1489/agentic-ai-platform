from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from .auth import current_session
from .database import get_db
from .models import Agent, Session as LoginSession, User

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

@router.post("", status_code=201)
def create_agent(data: AgentInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Agent name is required")
    agent = Agent(owner_id=auth[0].id, name=name, description=data.description.strip(),
                  instructions=data.instructions.strip(), model=data.model.strip(), status="draft")
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
