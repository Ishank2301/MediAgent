"""
Medication Adherence & Reminder Service
Tracks medications, schedules, doses taken, and adherence stats.
"""
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Date, create_engine, Float
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./mediagent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Medication(Base):
    __tablename__ = "medications"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = Column(String, index=True, default="demo_user")
    name        = Column(String, nullable=False)
    dosage      = Column(String)           # e.g. "500mg"
    frequency   = Column(String)           # e.g. "twice_daily", "once_daily", "three_times_daily"
    times       = Column(Text)             # JSON list of times e.g. '["08:00","20:00"]'
    notes       = Column(Text)
    start_date  = Column(Date, default=date.today)
    end_date    = Column(Date, nullable=True)
    active      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class DoseLog(Base):
    __tablename__ = "dose_logs"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(String, index=True)
    user_id       = Column(String, index=True)
    scheduled_for = Column(DateTime)
    taken_at      = Column(DateTime, nullable=True)
    status        = Column(String, default="pending")   # pending | taken | missed | skipped
    notes         = Column(Text, nullable=True)


Base.metadata.create_all(bind=engine)


# ── Medication CRUD ───────────────────────────────────────────────────────────

def add_medication(user_id: str, name: str, dosage: str, frequency: str,
                   times: list[str], notes: str = "", start_date: str = None,
                   end_date: str = None) -> dict:
    import json
    db = SessionLocal()
    med = Medication(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=name,
        dosage=dosage,
        frequency=frequency,
        times=json.dumps(times),
        notes=notes,
        start_date=date.fromisoformat(start_date) if start_date else date.today(),
        end_date=date.fromisoformat(end_date) if end_date else None,
    )
    db.add(med)
    db.commit()
    db.refresh(med)
    result = _med_to_dict(med)
    db.close()
    return result


def get_medications(user_id: str, active_only: bool = True) -> list:
    db = SessionLocal()
    q = db.query(Medication).filter(Medication.user_id == user_id)
    if active_only:
        q = q.filter(Medication.active == True)
    meds = q.order_by(Medication.created_at).all()
    result = [_med_to_dict(m) for m in meds]
    db.close()
    return result


def update_medication(med_id: str, **kwargs) -> dict | None:
    import json
    db = SessionLocal()
    med = db.query(Medication).filter(Medication.id == med_id).first()
    if not med:
        db.close()
        return None
    for k, v in kwargs.items():
        if k == "times" and isinstance(v, list):
            v = json.dumps(v)
        if hasattr(med, k):
            setattr(med, k, v)
    db.commit()
    db.refresh(med)
    result = _med_to_dict(med)
    db.close()
    return result


def delete_medication(med_id: str) -> bool:
    db = SessionLocal()
    med = db.query(Medication).filter(Medication.id == med_id).first()
    if not med:
        db.close()
        return False
    med.active = False   # soft delete
    db.commit()
    db.close()
    return True


# ── Dose Logging ──────────────────────────────────────────────────────────────

def log_dose(medication_id: str, user_id: str, status: str = "taken",
             scheduled_for: str = None, notes: str = "") -> dict:
    db = SessionLocal()
    scheduled = datetime.fromisoformat(scheduled_for) if scheduled_for else datetime.utcnow()
    log = DoseLog(
        medication_id=medication_id,
        user_id=user_id,
        scheduled_for=scheduled,
        taken_at=datetime.utcnow() if status == "taken" else None,
        status=status,
        notes=notes,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    result = _log_to_dict(log)
    db.close()
    return result


def get_dose_logs(user_id: str, days: int = 7) -> list:
    db = SessionLocal()
    since = datetime.utcnow() - timedelta(days=days)
    logs = (db.query(DoseLog)
            .filter(DoseLog.user_id == user_id, DoseLog.scheduled_for >= since)
            .order_by(DoseLog.scheduled_for.desc())
            .all())
    result = [_log_to_dict(l) for l in logs]
    db.close()
    return result


def get_adherence_stats(user_id: str, days: int = 30) -> dict:
    """Calculate adherence percentage per medication."""
    db = SessionLocal()
    since = datetime.utcnow() - timedelta(days=days)
    logs = (db.query(DoseLog)
            .filter(DoseLog.user_id == user_id, DoseLog.scheduled_for >= since)
            .all())
    db.close()

    stats_by_med = {}
    for log in logs:
        mid = log.medication_id
        if mid not in stats_by_med:
            stats_by_med[mid] = {"taken": 0, "missed": 0, "skipped": 0, "total": 0}
        stats_by_med[mid]["total"] += 1
        stats_by_med[mid][log.status] = stats_by_med[mid].get(log.status, 0) + 1

    result = []
    for med_id, counts in stats_by_med.items():
        total = counts["total"]
        taken = counts.get("taken", 0)
        pct = round((taken / total) * 100, 1) if total > 0 else 0
        result.append({
            "medication_id": med_id,
            "adherence_pct": pct,
            "taken": taken,
            "missed": counts.get("missed", 0),
            "skipped": counts.get("skipped", 0),
            "total": total,
            "status": "good" if pct >= 80 else "fair" if pct >= 50 else "poor",
        })

    overall = 0
    if result:
        overall = round(sum(r["adherence_pct"] for r in result) / len(result), 1)

    return {"medications": result, "overall_adherence": overall, "days": days}


def get_todays_schedule(user_id: str) -> list:
    """Get today's medication schedule with taken/pending status."""
    import json
    db = SessionLocal()
    meds = db.query(Medication).filter(Medication.user_id == user_id, Medication.active == True).all()
    today = date.today()
    since = datetime.combine(today, datetime.min.time())
    until = since + timedelta(days=1)
    today_logs = (db.query(DoseLog)
                  .filter(DoseLog.user_id == user_id,
                          DoseLog.scheduled_for >= since,
                          DoseLog.scheduled_for < until)
                  .all())
    taken_ids = {l.medication_id for l in today_logs if l.status == "taken"}
    db.close()

    schedule = []
    for med in meds:
        if med.end_date and med.end_date < today:
            continue
        times = json.loads(med.times) if med.times else ["08:00"]
        for t in times:
            schedule.append({
                "medication_id": med.id,
                "name": med.name,
                "dosage": med.dosage,
                "time": t,
                "taken": med.id in taken_ids,
                "notes": med.notes,
            })
    schedule.sort(key=lambda x: x["time"])
    return schedule


# ── Helpers ───────────────────────────────────────────────────────────────────
def _med_to_dict(m: Medication) -> dict:
    import json
    return {
        "id": m.id, "user_id": m.user_id, "name": m.name, "dosage": m.dosage,
        "frequency": m.frequency, "times": json.loads(m.times) if m.times else [],
        "notes": m.notes, "active": m.active,
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _log_to_dict(l: DoseLog) -> dict:
    return {
        "id": l.id, "medication_id": l.medication_id, "user_id": l.user_id,
        "status": l.status, "notes": l.notes,
        "scheduled_for": l.scheduled_for.isoformat() if l.scheduled_for else None,
        "taken_at": l.taken_at.isoformat() if l.taken_at else None,
    }
