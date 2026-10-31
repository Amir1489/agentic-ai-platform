from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session as DBSession
from .ai_provider import AIProviderError, AIProviderNotConfigured, generate_reply, is_configured
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
def send_message(conversation_id: int, data: MessageInput, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    row = owned_conversation(conversation_id, auth[0].id, db)
    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    if not is_configured():
        raise HTTPException(status_code=503, detail="AI provider is not configured. Set AI_API_KEY on the backend.")

    # Build context without persisting a user message until the provider succeeds.
    previous = db.scalars(
        select(ChatMessage).where(ChatMessage.conversation_id == row.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(19)
    ).all()
    previous.reverse()
    payload = [{"role": item.role, "content": item.content} for item in previous]
    payload.append({"role": "user", "content": content})

    try:
        answer = generate_reply(payload)
    except AIProviderNotConfigured:
        raise HTTPException(status_code=503, detail="AI provider is not configured. Set AI_API_KEY on the backend.")
    except AIProviderError:
        raise HTTPException(status_code=502, detail="The AI provider is temporarily unavailable.")

    user_message = ChatMessage(conversation_id=row.id, role="user", content=content)
    assistant_message = ChatMessage(conversation_id=row.id, role="assistant", content=answer)
    db.add_all([user_message, assistant_message])
    if row.title in ("New conversation", "گفتگوی جدید"):
        row.title = content[:80]
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return {
        "user_message": {"id": user_message.id, "role": user_message.role, "content": user_message.content, "created": user_message.created_at.isoformat()},
        "assistant_message": {"id": assistant_message.id, "role": assistant_message.role, "content": assistant_message.content, "created": assistant_message.created_at.isoformat()},
    }

@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, auth: tuple[User, LoginSession] = Depends(current_session), db: DBSession = Depends(get_db)):
    row = owned_conversation(conversation_id, auth[0].id, db)
    db.delete(row)
    db.commit()
