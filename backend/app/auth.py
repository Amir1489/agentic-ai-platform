import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from .database import get_db
from .models import Session, User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
SESSION_DAYS = 7

def digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def issue_session(db: DBSession, user: User) -> str:
    token = secrets.token_urlsafe(48)
    db.add(Session(user_id=user.id, token_hash=digest(token), expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)))
    db.commit()
    return token

def current_session(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: DBSession = Depends(get_db)) -> tuple[User, Session]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    session = db.scalar(select(Session).where(Session.token_hash == digest(credentials.credentials)))
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
    if expires <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user, session
