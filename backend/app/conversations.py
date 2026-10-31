from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DBSession
from .auth import current_session
from .database import get_db
from .models import ChatMessage, Conversation, Session as LoginSession, User

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationInput(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=12000)


def serialize_conversation(row: Conversation, db: DBSession):
    count = db.scalar(select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == row.id)) or 0
    return {"id": row.id, "title": row.title, "created": row.created_at.isoformat(), "updated": row.updated_at.isoformat(), "message_count": count}


def owned_conversation(conversation_id: int, user_id: int, db: DBSession):
    row = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.owner_id == user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return row


@router.get("")
def list_conversations(auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    rows = db.scalars(select(Conversation).where(Conversation.owner_id == auth[0].id).order_by(Conversation.updated_at.desc())).all()
    return [serialize_conversation(row, db) for row in rows]


@router.post("", status_code=201)
def create_conversation(data: ConversationInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    title = data.title.strip() or "New conversation"
    row = Conversation(owner_id=auth[0].id, title=title)
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_conversation(row, db)


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    owned_conversation(conversation_id, auth[0].id, db)
    rows = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at, ChatMessage.id)).all()
    return [{"id": row.id, "role": row.role, "content": row.content, "created": row.created_at.isoformat()} for row in rows]


@router.post("/{conversation_id}/messages", status_code=201)
def save_message(conversation_id: int, data: MessageInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    row = owned_conversation(conversation_id, auth[0].id, db)
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    message = ChatMessage(conversation_id=row.id, role="user", content=content)
    db.add(message)
    if row.title == "New conversation":
        row.title = content[:80]
    db.commit()
    db.refresh(message)
    return {"id": message.id, "role": message.role, "content": message.content, "created": message.created_at.isoformat(), "notice": "Message saved. AI responses will be enabled after a model provider is configured."}


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    row = owned_conversation(conversation_id, auth[0].id, db)
    db.delete(row)
    db.commit()
