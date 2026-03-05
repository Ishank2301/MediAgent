"""Notification API — email & WhatsApp for meds, appointments, adherence reports."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional, List

from backend.services.email_service import (
    send_medication_reminder, send_weekly_adherence_report,
    send_missed_dose_alert, send_email,
)
from backend.services.whatsapp_service import (
    send_medication_whatsapp, send_weekly_summary_whatsapp,
    send_missed_dose_whatsapp, send_whatsapp,
)
from backend.services.adherence_service import get_adherence_stats, get_todays_schedule

log    = logging.getLogger("mediagent.api.notifications")
router = APIRouter()


# ── Input models ──────────────────────────────────────────────────────────────

class TestNotifRequest(BaseModel):
    channel: str
    to:      str
    message: str = "✚ MediAgent test — your notifications are working!"

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, v):
        if v not in {"email", "whatsapp"}:
            raise ValueError("channel must be 'email' or 'whatsapp'")
        return v

    @field_validator("to")
    @classmethod
    def non_empty_to(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("'to' field is required")
        return v


class MedReminderRequest(BaseModel):
    user_id:  str = "demo_user"
    channels: List[str] = ["email"]
    email:    Optional[str] = None
    phone:    Optional[str] = None

    @field_validator("channels")
    @classmethod
    def valid_channels(cls, v):
        for ch in v:
            if ch not in {"email", "whatsapp"}:
                raise ValueError(f"Invalid channel: {ch}")
        return v


class AdherenceReportRequest(BaseModel):
    user_id:     str = "demo_user"
    channels:    List[str] = ["email"]
    email:       Optional[str] = None
    phone:       Optional[str] = None
    days:        int = 7
    include_pdf: bool = False

    @field_validator("days")
    @classmethod
    def valid_days(cls, v):
        return max(1, min(v, 90))


class MissedDoseRequest(BaseModel):
    medication_name: str
    dosage:          str = ""
    email:           Optional[str] = None
    phone:           Optional[str] = None

    @field_validator("medication_name")
    @classmethod
    def non_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("medication_name is required")
        return v[:100]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/notify/test")
def test_notification(req: TestNotifRequest):
    """Send a test message to verify credentials work."""
    if req.channel == "email":
        from backend.services.email_service import _wrap, _header_tpl
        html = _wrap(
            _header_tpl("Test Notification"),
            f"<h2>✅ Test Successful</h2><p>{req.message}</p>"
        )
        return send_email(req.to, "✚ MediAgent — Test Notification", html, req.message)

    elif req.channel == "whatsapp":
        return send_whatsapp(req.to, req.message)


@router.post("/notify/medications")
def notify_medications(req: MedReminderRequest):
    """Send today's pending medications as a reminder."""
    try:
        schedule = get_todays_schedule(req.user_id)
    except Exception as e:
        raise HTTPException(500, f"Could not load schedule: {e}")

    pending = [s for s in schedule if not s.get("taken")]
    if not pending:
        return {"message": "No pending medications to remind about", "count": 0}

    results = {}

    if "email" in req.channels:
        if not req.email:
            results["email"] = {"success": False, "message": "No email address provided"}
        else:
            results["email"] = send_medication_reminder(req.email, pending)

    if "whatsapp" in req.channels:
        if not req.phone:
            results["whatsapp"] = {"success": False, "message": "No phone number provided"}
        else:
            results["whatsapp"] = send_medication_whatsapp(req.phone, pending)

    return {"medications_count": len(pending), "results": results}


@router.post("/notify/adherence-report")
def notify_adherence(req: AdherenceReportRequest):
    """Send adherence summary. Email version can include PDF attachment."""
    try:
        stats = get_adherence_stats(req.user_id, req.days)
    except Exception as e:
        raise HTTPException(500, f"Could not load adherence stats: {e}")

    pdf_bytes = None
    if req.include_pdf and "email" in req.channels:
        try:
            from backend.services.pdf_service import generate_adherence_report
            from backend.services.adherence_service import get_medications, get_dose_logs
            meds = get_medications(req.user_id, active_only=False)
            logs = get_dose_logs(req.user_id, req.days)
            pdf_bytes = generate_adherence_report(req.user_id, stats, meds, logs)
        except Exception as e:
            log.warning("PDF generation failed (non-fatal): %s", e)

    results = {}
    if "email" in req.channels:
        if not req.email:
            results["email"] = {"success": False, "message": "No email address provided"}
        else:
            results["email"] = send_weekly_adherence_report(req.email, stats, pdf_bytes)

    if "whatsapp" in req.channels:
        if not req.phone:
            results["whatsapp"] = {"success": False, "message": "No phone number provided"}
        else:
            results["whatsapp"] = send_weekly_summary_whatsapp(req.phone, stats)

    return {
        "adherence_pct": stats.get("overall_adherence"),
        "days":          req.days,
        "results":       results,
    }


@router.post("/notify/missed-dose")
def notify_missed_dose(req: MissedDoseRequest):
    """Alert user about a missed dose via email and/or WhatsApp."""
    if not req.email and not req.phone:
        raise HTTPException(400, "Provide at least one of: email, phone")

    results = {}
    if req.email:
        results["email"] = send_missed_dose_alert(req.email, req.medication_name, req.dosage)
    if req.phone:
        results["whatsapp"] = send_missed_dose_whatsapp(req.phone, req.medication_name, req.dosage)
    return results
