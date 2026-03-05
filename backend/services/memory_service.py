"""
Memory Service — SQLite-based conversation history.
From project1, enhanced with query filtering and pagination.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, desc
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./mediagent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    mode = Column(String)         # symptom | interaction | prescription
    user_input = Column(Text)
    response = Column(Text)
    triage_level = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def save_memory(
    user_id: str,
    mode: str,
    user_input: str,
    response: str,
    triage_level: str = None,
    risk_level: str = None,
) -> Conversation:
    db = SessionLocal()
    record = Conversation(
        user_id=user_id,
        mode=mode,
        user_input=user_input,
        response=response,
        triage_level=triage_level,
        risk_level=risk_level,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    db.close()
    return record


def get_history(user_id: str, limit: int = 50, mode: str = None) -> list:
    db = SessionLocal()
    query = db.query(Conversation).filter(Conversation.user_id == user_id)
    if mode:
        query = query.filter(Conversation.mode == mode)
    records = query.order_by(desc(Conversation.timestamp)).limit(limit).all()
    result = [
        {
            "id": r.id,
            "mode": r.mode,
            "user_input": r.user_input,
            "response": r.response,
            "triage_level": r.triage_level,
            "risk_level": r.risk_level,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in records
    ]
    db.close()
    return result


def delete_history(user_id: str) -> int:
    db = SessionLocal()
    deleted = db.query(Conversation).filter(Conversation.user_id == user_id).delete()
    db.commit()
    db.close()
    return deleted
