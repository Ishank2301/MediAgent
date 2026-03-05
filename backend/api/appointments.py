"""Appointment planner API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.services.appointment_service import (
    create_appointment, get_appointments, get_appointment,
    update_appointment, delete_appointment, get_due_reminders, mark_reminder_sent,
)
from backend.services.email_service import send_appointment_reminder
from backend.services.whatsapp_service import send_appointment_whatsapp

router = APIRouter()


class AppointmentCreate(BaseModel):
    user_id: str = "demo_user"
    title: str
    doctor_name: str = ""
    clinic: str = ""
    location: str = ""
    scheduled_at: str           # ISO format: "2024-03-15T09:00:00"
    duration_mins: int = 30
    notes: str = ""
    email: str = ""
    phone: str = ""


class AppointmentUpdate(BaseModel):
    title: Optional[str] = None
    doctor_name: Optional[str] = None
    clinic: Optional[str] = None
    location: Optional[str] = None
    scheduled_at: Optional[str] = None
    duration_mins: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class SendReminderRequest(BaseModel):
    channels: list[str] = ["email"]   # ["email", "whatsapp"]


@router.get("/appointments")
def list_appointments(user_id: str = "demo_user", upcoming_only: bool = False):
    return get_appointments(user_id, upcoming_only)


@router.post("/appointments")
def book_appointment(req: AppointmentCreate):
    return create_appointment(
        user_id=req.user_id, title=req.title, doctor_name=req.doctor_name,
        clinic=req.clinic, location=req.location, scheduled_at=req.scheduled_at,
        duration_mins=req.duration_mins, notes=req.notes,
        email=req.email, phone=req.phone,
    )


@router.get("/appointments/{apt_id}")
def get_one(apt_id: str):
    a = get_appointment(apt_id)
    if not a:
        raise HTTPException(404, "Appointment not found")
    return a


@router.patch("/appointments/{apt_id}")
def edit_appointment(apt_id: str, req: AppointmentUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    result = update_appointment(apt_id, **updates)
    if not result:
        raise HTTPException(404, "Appointment not found")
    return result


@router.delete("/appointments/{apt_id}")
def cancel_appointment(apt_id: str):
    if not delete_appointment(apt_id):
        raise HTTPException(404, "Appointment not found")
    return {"cancelled": True}


@router.post("/appointments/{apt_id}/remind")
def send_reminder(apt_id: str, req: SendReminderRequest):
    """Manually trigger a reminder for a specific appointment."""
    apt = get_appointment(apt_id)
    if not apt:
        raise HTTPException(404, "Appointment not found")

    results = {}

    if "email" in req.channels:
        if not apt.get("email"):
            results["email"] = {"success": False, "message": "No email on file for this appointment"}
        else:
            results["email"] = send_appointment_reminder(apt["email"], apt)

    if "whatsapp" in req.channels:
        if not apt.get("phone"):
            results["whatsapp"] = {"success": False, "message": "No phone on file for this appointment"}
        else:
            results["whatsapp"] = send_appointment_whatsapp(apt["phone"], apt)

    mark_reminder_sent(apt_id)
    return {"appointment_id": apt_id, "results": results}


@router.post("/appointments/remind/auto")
def auto_remind(hours_ahead: int = 24):
    """Send reminders for all appointments due within N hours (call from scheduler)."""
    due = get_due_reminders(hours_ahead)
    sent = []
    for apt in due:
        result = {}
        if apt.get("email"):
            result["email"] = send_appointment_reminder(apt["email"], apt)
        if apt.get("phone"):
            result["whatsapp"] = send_appointment_whatsapp(apt["phone"], apt)
        mark_reminder_sent(apt["id"])
        sent.append({"appointment_id": apt["id"], "title": apt["title"], "results": result})
    return {"processed": len(sent), "appointments": sent}
