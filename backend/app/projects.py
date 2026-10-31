from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from .auth import current_session
from .database import get_db
from .models import Project, Session as LoginSession, User

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)

def serialize(project: Project):
    return {"id": project.id, "name": project.name, "created": project.created_at.isoformat()}

@router.get("")
def list_projects(auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    rows = db.scalars(select(Project).where(Project.owner_id == auth[0].id).order_by(Project.created_at.desc())).all()
    return [serialize(row) for row in rows]

@router.post("", status_code=201)
def create_project(data: ProjectInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Project name is required")
    project = Project(owner_id=auth[0].id, name=name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize(project)

@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == auth[0].id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
