"""
WhatsApp Notification Service via Twilio API.
Includes input validation, retry logic, phone normalisation.

Setup (free):
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_token
  TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

Join sandbox: text "join <word>" to +1 415 523 8886 from WhatsApp.
"""
import os, re, logging, time
import requests as req
from datetime import datetime

log = logging.getLogger("mediagent.whatsapp")

TWILIO_SID    = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN",  "").strip()
TWILIO_FROM   = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886").strip()

MAX_RETRIES   = 2
RETRY_DELAY   = 2
WA_CHAR_LIMIT = 1600   # Twilio WhatsApp max message length

PHONE_REGEX   = re.compile(r"^\+[1-9]\d{7,14}$")


def _configured() -> bool:
    return bool(TWILIO_SID and TWILIO_TOKEN)


def _normalise_phone(phone: str) -> str:
    """Clean and validate phone number. Returns whatsapp:+XXXXXXXXX or raises ValueError."""
    # Strip whatsapp: prefix if present
    p = phone.strip()
    if p.lower().startswith("whatsapp:"):
        p = p[9:]
    # Remove spaces, dashes, parens
    p = re.sub(r"[\s\-\(\)]", "", p)
    # Add + if missing
    if not p.startswith("+"):
        p = "+" + p
    if not PHONE_REGEX.match(p):
        raise ValueError(
            f"Invalid phone number '{phone}'. "
            "Use international format: +CountryCodeNumber (e.g. +14155551234)"
        )
    return f"whatsapp:{p}"


def send_whatsapp(to: str, message: str) -> dict:
    """Core send function. Returns {"success": bool, "message": str}."""
    # Validate phone
    try:
        to_wa = _normalise_phone(to)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    # Check credentials
    if not _configured():
        return {
            "success":   False,
            "simulated": True,
            "message":   "WhatsApp not configured — set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env",
            "to":        to,
            "preview":   message[:150],
        }

    # Truncate if over limit
    if len(message) > WA_CHAR_LIMIT:
        message = message[:WA_CHAR_LIMIT - 3] + "…"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = req.post(
                url,
                data={"From": TWILIO_FROM, "To": to_wa, "Body": message},
                auth=(TWILIO_SID, TWILIO_TOKEN),
                timeout=15,
            )
            data = resp.json()

            if resp.status_code in (200, 201):
                log.info("WhatsApp sent to %s (SID: %s)", to, data.get("sid", ""))
                return {"success": True, "message": f"WhatsApp delivered to {to}", "sid": data.get("sid")}

            # Handle Twilio errors
            code = data.get("code")
            err  = data.get("message", f"HTTP {resp.status_code}")

            friendly = {
                20003: "Twilio authentication failed — check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN",
                21211: "Invalid 'To' phone number format",
                21408: "Permission to send to this region is not enabled in your Twilio account",
                21610: "Unsubscribed number — recipient opted out of WhatsApp messages",
                21614: "Not a valid mobile number",
                63001: "WhatsApp channel error — ensure the sandbox is active",
                63003: "Recipient has not joined the WhatsApp sandbox (they need to text \"join\" first)",
                63016: "Template not approved or missing for this message type",
            }
            err_msg = friendly.get(code, f"Twilio error {code}: {err}")

            if resp.status_code == 401:
                return {"success": False, "message": friendly[20003]}
            if resp.status_code >= 500:
                log.warning("Twilio server error attempt %d: %s", attempt, err)
            else:
                return {"success": False, "message": err_msg, "code": code}

        except req.exceptions.Timeout:
            err = "Request to Twilio timed out"
        except req.exceptions.ConnectionError:
            err = "Cannot reach Twilio API — check internet connection"
        except Exception as e:
            return {"success": False, "message": f"Unexpected error: {e}"}

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return {"success": False, "message": err}


# ── Message templates ─────────────────────────────────────────────────────────

def send_appointment_whatsapp(phone: str, appointment: dict) -> dict:
    apt_time = appointment.get("scheduled_at", "")[:16].replace("T", " ")
    title    = appointment.get("title", "Appointment")
    doctor   = appointment.get("doctor_name") or "N/A"
    clinic   = appointment.get("clinic") or "N/A"
    location = appointment.get("location") or "N/A"
    duration = appointment.get("duration_mins", 30)
    notes    = appointment.get("notes", "")

    msg = (
        f"✚ *MediAgent — Appointment Reminder*\n\n"
        f"📅 *{title}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👨‍⚕️ *Doctor:* {doctor}\n"
        f"🏥 *Clinic:* {clinic}\n"
        f"📍 *Location:* {location}\n"
        f"🕐 *When:* {apt_time}\n"
        f"⏱ *Duration:* {duration} minutes\n"
    )
    if notes:
        msg += f"\n📝 _{notes}_\n"
    msg += "\n_Please confirm your appointment with your healthcare provider._"
    return send_whatsapp(phone, msg)


def send_medication_whatsapp(phone: str, medications: list) -> dict:
    if not medications:
        return {"success": False, "message": "No medications to send"}
    lines = "\n".join(
        f"  {'✅' if m.get('taken') else '⏰'} *{m.get('name','')}* "
        f"{m.get('dosage','')} — {m.get('time','')}"
        for m in medications[:10]   # cap at 10 to stay under char limit
    )
    count = len(medications)
    msg = (
        f"✚ *MediAgent — Medication Reminder*\n\n"
        f"💊 You have *{count} medication{'s' if count > 1 else ''}* due:\n\n"
        f"{lines}\n\n"
        f"_Open MediAgent to log your doses._"
    )
    return send_whatsapp(phone, msg)


def send_missed_dose_whatsapp(phone: str, medication_name: str, dosage: str = "") -> dict:
    msg = (
        f"✚ *MediAgent — Missed Dose Alert* ⚠️\n\n"
        f"You may have missed:\n"
        f"💊 *{medication_name}* {dosage}\n\n"
        f"Take it as soon as possible unless it's close to your next dose.\n"
        f"Never double-dose — consult your doctor if unsure.\n\n"
        f"_Reply STOP to unsubscribe from reminders._"
    )
    return send_whatsapp(phone, msg)


def send_weekly_summary_whatsapp(phone: str, stats: dict) -> dict:
    overall = int(stats.get("overall_adherence", 0))
    days    = stats.get("days", 7)
    emoji   = "✅" if overall >= 80 else "⚠️" if overall >= 50 else "❗"
    label   = "Excellent" if overall >= 80 else "Fair" if overall >= 50 else "Needs attention"

    msg = (
        f"✚ *MediAgent — Weekly Report*\n\n"
        f"{emoji} *Overall Adherence: {overall}%* — {label}\n"
        f"📅 Last {days} days\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )
    for m in stats.get("medications", [])[:6]:
        pct  = int(m.get("adherence_pct", 0))
        ico  = "✅" if pct >= 80 else "⚠️" if pct >= 50 else "❗"
        name = str(m.get("medication_id", "Med"))[:15]
        taken = m.get("taken", 0)
        total = m.get("total", 0)
        msg += f"{ico} {name}: *{pct}%* ({taken}/{total} doses)\n"

    msg += "\n_Full report available in MediAgent app._"
    return send_whatsapp(phone, msg)
