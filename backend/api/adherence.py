"""Medication adherence & reminder API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from backend.services.adherence_service import (
    add_medication, get_medications, update_medication, delete_medication,
    log_dose, get_dose_logs, get_adherence_stats, get_todays_schedule,
)

router = APIRouter()


class MedicationCreate(BaseModel):
    user_id: str = "demo_user"
    name: str
    dosage: str = ""
    frequency: str = "once_daily"
    times: List[str] = ["08:00"]
    notes: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    times: Optional[List[str]] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    end_date: Optional[str] = None


class DoseLogCreate(BaseModel):
    user_id: str = "demo_user"
    status: str = "taken"
    scheduled_for: Optional[str] = None
    notes: str = ""


@router.get("/medications")
def list_medications(user_id: str = "demo_user", active_only: bool = True):
    return get_medications(user_id, active_only)


@router.post("/medications")
def create_medication(req: MedicationCreate):
    return add_medication(
        user_id=req.user_id, name=req.name, dosage=req.dosage,
        frequency=req.frequency, times=req.times, notes=req.notes,
        start_date=req.start_date, end_date=req.end_date,
    )


@router.patch("/medications/{med_id}")
def edit_medication(med_id: str, req: MedicationUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = update_medication(med_id, **updates)
    if not result:
        raise HTTPException(404, "Medication not found")
    return result


@router.delete("/medications/{med_id}")
def remove_medication(med_id: str):
    if not delete_medication(med_id):
        raise HTTPException(404, "Medication not found")
    return {"deleted": True}


@router.post("/medications/{med_id}/log")
def record_dose(med_id: str, req: DoseLogCreate):
    return log_dose(med_id, req.user_id, req.status, req.scheduled_for, req.notes)


@router.get("/adherence")
def adherence(user_id: str = "demo_user", days: int = 30):
    return get_adherence_stats(user_id, days)


@router.get("/schedule")
def todays_schedule(user_id: str = "demo_user"):
    return get_todays_schedule(user_id)


@router.get("/dose-logs")
def dose_logs(user_id: str = "demo_user", days: int = 7):
    return get_dose_logs(user_id, days)
