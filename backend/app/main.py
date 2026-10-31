import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from .auth import current_session, digest, issue_session, password_hash
from .database import Base, engine, get_db
from .models import User, Session as LoginSession
from .projects import router as projects_router
from .conversations import router as conversations_router
from .agents import router as agents_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Agentic AI Platform API", version="0.2.0", lifespan=lifespan)
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,https://amir1489.github.io").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class LoginCredentials(BaseModel):
    email: EmailStr
    password: str

def public_user(user: User) -> dict:
    return {"id": user.id, "email": user.email}

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "agentic-ai-platform"}

@app.get("/api/ready")
def ready():
    """Readiness check: confirms the configured database accepts a simple query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database is not ready")
    return {"status": "ready", "database": "reachable"}

@app.post("/api/auth/register", status_code=201)
def register(data: Credentials, db: DBSession = Depends(get_db)):
    email = str(data.email).lower()
    user = User(email=email, password_hash=password_hash.hash(data.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return {"token": issue_session(db, user), "user": public_user(user)}

@app.post("/api/auth/login")
def login(data: LoginCredentials, db: DBSession = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if user is None or not password_hash.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": issue_session(db, user), "user": public_user(user)}

@app.get("/api/auth/me")
def me(auth: tuple[User, LoginSession] = Depends(current_session)):
    return public_user(auth[0])

@app.post("/api/auth/logout", status_code=204)
def logout(auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    db.delete(auth[1])
    db.commit()

app.include_router(projects_router)
app.include_router(conversations_router)
app.include_router(agents_router)
