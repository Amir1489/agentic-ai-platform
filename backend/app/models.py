from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class AuthRateLimitBucket(Base):
    __tablename__ = "auth_rate_limit_buckets"
    bucket_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(String(12000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500), default="")
    instructions: Mapped[str] = mapped_column(String(4000), default="")
    model: Mapped[str] = mapped_column(String(100), default="gpt-4o-mini")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    input: Mapped[str] = mapped_column(String(8000))
    output: Mapped[str] = mapped_column(String(12000), default="")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class AgentTaskEvent(Base):
    __tablename__ = "agent_task_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
