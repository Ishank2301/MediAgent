"""
Session Service — persistent multi-turn chat sessions.
Each session has a mode (symptom/interaction/prescription/general),
a title, and full message history stored in SQLite.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    create_engine,
    ForeignKey,
    desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ── Database Setup ──────────────────────────────────────────────

DATABASE_URL = "sqlite:///./mediagent.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ── Models ───────────────────────────────────────────────────────


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, default="demo_user")
    title = Column(String, default="New Chat")
    mode = Column(
        String, default="general"
    )  # general | symptom | interaction | prescription
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.timestamp",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), index=True)
    role = Column(String)  # user | assistant | system
    content = Column(Text)
    meta = Column(Text, nullable=True)  # optional JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


Base.metadata.create_all(bind=engine)


# ── Session CRUD ─────────────────────────────────────────────────


def create_session(
    user_id: str = "demo_user", mode: str = "general", title: str = "New Chat"
) -> dict:
    db = SessionLocal()
    try:
        s = ChatSession(id=str(uuid.uuid4()), user_id=user_id, mode=mode, title=title)
        db.add(s)
        db.commit()
        db.refresh(s)
        return _session_to_dict(s)
    finally:
        db.close()


def get_sessions(user_id: str = "demo_user") -> list:
    db = SessionLocal()
    try:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
            .all()
        )
        return [_session_to_dict(s) for s in sessions]
    finally:
        db.close()


def get_session(session_id: str) -> dict | None:
    db = SessionLocal()
    try:
        s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not s:
            return None
        return _session_to_dict(s, include_messages=True)
    finally:
        db.close()


def rename_session(session_id: str, title: str) -> dict | None:
    db = SessionLocal()
    try:
        s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not s:
            return None

        s.title = title
        s.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(s)
        return _session_to_dict(s)
    finally:
        db.close()


def delete_session(session_id: str) -> bool:
    db = SessionLocal()
    try:
        s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not s:
            return False

        db.delete(s)
        db.commit()
        return True
    finally:
        db.close()


def add_message(session_id: str, role: str, content: str, meta: str = None) -> dict:

    db = SessionLocal()
    try:
        # Count existing messages BEFORE adding
        existing_count = (
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
        )

        msg = ChatMessage(session_id=session_id, role=role, content=content, meta=meta)

        db.add(msg)

        # Update session timestamp + auto-title
        s = db.query(ChatSession).filter(ChatSession.id == session_id).first()

        if s:
            s.updated_at = datetime.utcnow()

            # First user message → auto title
            if existing_count == 0 and role == "user" and s.title == "New Chat":
                s.title = content[:50] + ("..." if len(content) > 50 else "")

        db.commit()
        db.refresh(msg)
        return _msg_to_dict(msg)

    finally:
        db.close()


def get_messages(session_id: str) -> list:
    db = SessionLocal()
    try:
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp)
            .all()
        )
        return [_msg_to_dict(m) for m in msgs]
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────


def _session_to_dict(s: ChatSession, include_messages: bool = False) -> dict:

    data = {
        "id": s.id,
        "user_id": s.user_id,
        "title": s.title,
        "mode": s.mode,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "message_count": len(s.messages) if s.messages else 0,
    }

    if include_messages:
        data["messages"] = [_msg_to_dict(m) for m in s.messages]

    return data


def _msg_to_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "session_id": m.session_id,
        "role": m.role,
        "content": m.content,
        "meta": m.meta,
        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
    }
