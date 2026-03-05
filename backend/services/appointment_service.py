"""
Appointment Service — manages doctor appointments with reminders.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Text, DateTime, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./mediagent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Appointment(Base):
    __tablename__ = "appointments"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, index=True, default="demo_user")
    title         = Column(String, nullable=False)          # e.g. "Cardiology Checkup"
    doctor_name   = Column(String, default="")
    clinic        = Column(String, default="")
    location      = Column(String, default="")
    scheduled_at  = Column(DateTime, nullable=False)
    duration_mins = Column(String, default="30")
    notes         = Column(Text, default="")
    status        = Column(String, default="upcoming")      # upcoming | completed | cancelled
    reminder_sent = Column(Boolean, default=False)
    email         = Column(String, default="")
    phone         = Column(String, default="")
    created_at    = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def create_appointment(user_id: str, title: str, doctor_name: str, clinic: str,
                       location: str, scheduled_at: str, duration_mins: int = 30,
                       notes: str = "", email: str = "", phone: str = "") -> dict:
    db = SessionLocal()
    apt = Appointment(
        id=str(uuid.uuid4()),
        user_id=user_id, title=title, doctor_name=doctor_name,
        clinic=clinic, location=location,
        scheduled_at=datetime.fromisoformat(scheduled_at),
        duration_mins=str(duration_mins), notes=notes,
        email=email, phone=phone,
    )
    db.add(apt); db.commit(); db.refresh(apt)
    result = _to_dict(apt); db.close()
    return result


def get_appointments(user_id: str, upcoming_only: bool = False) -> list:
    db = SessionLocal()
    q = db.query(Appointment).filter(Appointment.user_id == user_id)
    if upcoming_only:
        q = q.filter(Appointment.scheduled_at >= datetime.utcnow(),
                     Appointment.status == "upcoming")
    apts = q.order_by(Appointment.scheduled_at).all()
    result = [_to_dict(a) for a in apts]
    db.close(); return result


def get_appointment(apt_id: str) -> dict | None:
    db = SessionLocal()
    a = db.query(Appointment).filter(Appointment.id == apt_id).first()
    result = _to_dict(a) if a else None
    db.close(); return result


def update_appointment(apt_id: str, **kwargs) -> dict | None:
    db = SessionLocal()
    a = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not a: db.close(); return None
    for k, v in kwargs.items():
        if k == "scheduled_at" and isinstance(v, str):
            v = datetime.fromisoformat(v)
        if hasattr(a, k): setattr(a, k, v)
    db.commit(); db.refresh(a)
    result = _to_dict(a); db.close(); return result


def delete_appointment(apt_id: str) -> bool:
    db = SessionLocal()
    a = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not a: db.close(); return False
    a.status = "cancelled"; db.commit(); db.close(); return True


def get_due_reminders(hours_ahead: int = 24) -> list:
    """Get appointments due for reminders within the next N hours."""
    db = SessionLocal()
    now = datetime.utcnow()
    cutoff = now + timedelta(hours=hours_ahead)
    apts = (db.query(Appointment)
            .filter(Appointment.scheduled_at >= now,
                    Appointment.scheduled_at <= cutoff,
                    Appointment.status == "upcoming",
                    Appointment.reminder_sent == False)
            .all())
    result = [_to_dict(a) for a in apts]
    db.close(); return result


def mark_reminder_sent(apt_id: str):
    db = SessionLocal()
    a = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if a: a.reminder_sent = True; db.commit()
    db.close()


def _to_dict(a: Appointment) -> dict:
    return {
        "id": a.id, "user_id": a.user_id, "title": a.title,
        "doctor_name": a.doctor_name, "clinic": a.clinic,
        "location": a.location, "duration_mins": a.duration_mins,
        "notes": a.notes, "status": a.status,
        "email": a.email, "phone": a.phone,
        "reminder_sent": a.reminder_sent,
        "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
