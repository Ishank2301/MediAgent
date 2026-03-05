"""
Email Notification Service — Gmail SMTP with retry, input validation, HTML templates.
Uses smtplib (stdlib, no paid service needed).

Setup:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=your@gmail.com
  SMTP_PASS=xxxx xxxx xxxx xxxx  # Gmail App Password
"""
import os, re, smtplib, ssl, logging, time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from html import escape

log = logging.getLogger("mediagent.email")

SMTP_HOST    = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT    = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER    = os.getenv("SMTP_USER", "").strip()
SMTP_PASS    = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM    = os.getenv("SMTP_FROM", f"MediAgent <{SMTP_USER}>") if SMTP_USER else "MediAgent"

MAX_RETRIES  = 2
RETRY_DELAY  = 2   # seconds

# Brand colors
GREEN   = "#2d4a3e"
GREEN2  = "#3d6455"
SAGE    = "#8cb8a8"
CREAM   = "#fafaf9"
GRAY    = "#6b7a72"
BORDER  = "#e2e8e5"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def _configured() -> bool:
    return bool(SMTP_USER and SMTP_PASS)


def _validate_email(address: str) -> str:
    """Validate and normalise email address. Raises ValueError on invalid."""
    addr = address.strip().lower()
    if not addr or not EMAIL_REGEX.match(addr):
        raise ValueError(f"Invalid email address: '{address}'")
    return addr


def _header_tpl(subtitle: str = "") -> str:
    return f"""
<div style="background:linear-gradient(135deg,{GREEN} 0%,{GREEN2} 100%);
     color:white;padding:28px 32px;border-radius:14px 14px 0 0;">
  <table style="width:100%;border-collapse:collapse;"><tr>
    <td style="vertical-align:middle;">
      <span style="font-size:22px;font-weight:800;letter-spacing:-0.5px;">✚ MediAgent</span>
    </td>
    <td style="text-align:right;vertical-align:middle;">
      <span style="font-size:12px;opacity:0.75;">{escape(subtitle)}</span>
    </td>
  </tr></table>
</div>"""


def _footer_tpl() -> str:
    return f"""
<div style="padding:16px 32px;background:#f0f4f2;border-radius:0 0 14px 14px;
     border-top:1px solid {BORDER};">
  <p style="margin:0;color:{GRAY};font-size:11px;text-align:center;">
    ⚠️ MediAgent provides AI guidance only — not a substitute for professional medical advice.<br>
    Sent {datetime.now().strftime("%d %b %Y at %H:%M UTC")}
  </p>
</div>"""


def _wrap(header: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head><body style="margin:0;padding:20px;background:#eef2ef;font-family:'Helvetica Neue',Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;box-shadow:0 4px 20px rgba(0,0,0,0.1);border-radius:14px;">
  {header}
  <div style="background:{CREAM};padding:32px;border:1px solid {BORDER};border-top:none;">
    {body}
  </div>
  {_footer_tpl()}
</div>
</body></html>"""


def _row(label: str, value: str) -> str:
    return f"""
<tr>
  <td style="padding:9px 0;color:{GRAY};font-size:13px;width:130px;
      border-bottom:1px solid #f0f0ee;font-weight:600;">{escape(label)}</td>
  <td style="padding:9px 0;color:#1c1917;font-size:13px;
      border-bottom:1px solid #f0f0ee;">{escape(str(value))}</td>
</tr>"""


def send_email(to: str, subject: str, html_body: str,
               plain_body: str = "",
               attachment_bytes: bytes = None,
               attachment_name: str = None) -> dict:
    """Core send function. Returns {"success": bool, "message": str}."""
    # Validate
    try:
        to = _validate_email(to)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    if not _configured():
        return {
            "success":   False,
            "simulated": True,
            "message":   "Email not configured — set SMTP_USER and SMTP_PASS in .env",
            "to":        to,
            "subject":   subject,
        }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = SMTP_FROM
            msg["To"]      = to
            msg["X-Mailer"] = "MediAgent/5.0"

            if plain_body:
                msg.attach(MIMEText(plain_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if attachment_bytes and attachment_name:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_bytes)
                encoders.encode_base64(part)
                safe_name = re.sub(r'[^\w.\-]', '_', attachment_name)[:80]
                part.add_header("Content-Disposition", f'attachment; filename="{safe_name}"')
                msg.attach(part)

            ctx = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.login(SMTP_USER, SMTP_PASS)
                srv.sendmail(SMTP_FROM, [to], msg.as_bytes())

            log.info("Email sent to %s (attempt %d)", to, attempt)
            return {"success": True, "message": f"Email delivered to {to}"}

        except smtplib.SMTPAuthenticationError:
            return {"success": False, "message": "SMTP authentication failed — check SMTP_USER and SMTP_PASS (use Gmail App Password, not your login password)"}
        except smtplib.SMTPRecipientsRefused:
            return {"success": False, "message": f"Recipient address rejected by server: {to}"}
        except smtplib.SMTPConnectError as e:
            err = f"Cannot connect to {SMTP_HOST}:{SMTP_PORT} — {e}"
        except smtplib.SMTPException as e:
            err = f"SMTP error: {e}"
        except OSError as e:
            err = f"Network error: {e}"
        except Exception as e:
            err = f"Unexpected error: {e}"

        log.warning("Email attempt %d/%d failed: %s", attempt, MAX_RETRIES, err)
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return {"success": False, "message": err}


# ── Templates ─────────────────────────────────────────────────────────────────

def send_appointment_reminder(to: str, appointment: dict) -> dict:
    apt_time = appointment.get("scheduled_at", "")[:16].replace("T", " ")
    title    = appointment.get("title", "Appointment")
    doctor   = appointment.get("doctor_name") or "—"
    clinic   = appointment.get("clinic") or "—"
    loc      = appointment.get("location") or "—"
    dur      = appointment.get("duration_mins", 30)
    notes    = appointment.get("notes", "")

    rows  = (_row("Doctor", doctor) + _row("Clinic", clinic) +
             _row("Date & Time", apt_time) + _row("Location", loc) +
             _row("Duration", f"{dur} minutes"))
    notes_html = (f'<div style="background:#f5f0e8;padding:14px 16px;border-radius:8px;'
                  f'color:{GRAY};font-size:13px;margin-top:16px;">📝 {escape(notes)}</div>'
                  if notes else "")
    body = f"""
<h2 style="color:{GREEN};margin:0 0 20px;font-size:20px;">📅 {escape(title)}</h2>
<table style="width:100%;border-collapse:collapse;">{rows}</table>
{notes_html}
<div style="margin-top:24px;padding:16px;background:linear-gradient(135deg,{GREEN}15,{SAGE}20);
     border-radius:10px;border-left:3px solid {GREEN};">
  <p style="margin:0;font-size:13px;color:{GREEN};font-weight:600;">
    ✅ Please confirm this appointment directly with your healthcare provider.
  </p>
</div>"""
    plain = f"Appointment Reminder: {title}\nDate: {apt_time}\nDoctor: {doctor}\nLocation: {loc}"
    return send_email(to, f"📅 Reminder: {title}", _wrap(_header_tpl("Appointment Reminder"), body), plain)


def send_medication_reminder(to: str, medications: list) -> dict:
    if not medications:
        return {"success": False, "message": "No medications to remind about"}

    rows_html = "".join(
        f'<tr>'
        f'<td style="padding:12px 14px;border-bottom:1px solid #f5f5f4;font-weight:600;">💊 {escape(m.get("name",""))}</td>'
        f'<td style="padding:12px 14px;border-bottom:1px solid #f5f5f4;color:{GRAY};">{escape(m.get("dosage",""))}</td>'
        f'<td style="padding:12px 14px;border-bottom:1px solid #f5f5f4;color:{GRAY};">🕐 {escape(m.get("time",""))}</td>'
        f'</tr>'
        for m in medications
    )
    body = f"""
<h2 style="color:{GREEN};margin:0 0 20px;font-size:20px;">💊 Time for your medications</h2>
<table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;
     overflow:hidden;border:1px solid {BORDER};">
  <thead><tr style="background:#f5f5f4;">
    <th style="padding:11px 14px;text-align:left;color:{GRAY};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Medication</th>
    <th style="padding:11px 14px;text-align:left;color:{GRAY};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Dosage</th>
    <th style="padding:11px 14px;text-align:left;color:{GRAY};font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">Time</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>"""
    plain = "Medication Reminder:\n" + "\n".join(
        f"- {m.get('name')} {m.get('dosage')} at {m.get('time')}" for m in medications
    )
    return send_email(to, f"💊 Medication Reminder ({len(medications)} due)", _wrap(_header_tpl("Medication Reminder"), body), plain)


def send_missed_dose_alert(to: str, medication_name: str, dosage: str = "") -> dict:
    body = f"""
<h2 style="color:#d97706;margin:0 0 16px;">⚠️ Missed Dose Alert</h2>
<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:20px;">
  <p style="margin:0 0 10px;font-size:16px;">You may have missed a dose of:</p>
  <p style="margin:0;font-size:20px;font-weight:700;color:{GREEN};">
    💊 {escape(medication_name)} {escape(dosage)}
  </p>
</div>
<p style="font-size:13px;color:{GRAY};margin-top:20px;">
  Take it as soon as possible — unless it's close to your next scheduled dose, in which case skip this one.
  Never double-dose without consulting your doctor.
</p>"""
    plain = f"Missed Dose: {medication_name} {dosage}"
    return send_email(to, f"⚠️ Missed Dose: {medication_name}", _wrap(_header_tpl("Missed Dose Alert"), body), plain)


def send_weekly_adherence_report(to: str, stats: dict, pdf_bytes: bytes = None) -> dict:
    overall  = int(stats.get("overall_adherence", 0))
    color    = "#16a34a" if overall >= 80 else "#d97706" if overall >= 50 else "#dc2626"
    label    = "Excellent" if overall >= 80 else "Fair" if overall >= 50 else "Needs Attention"
    days     = stats.get("days", 7)

    bar_bg   = "#e8f5e9" if overall >= 80 else "#fff8e1" if overall >= 50 else "#fce4ec"
    bar_col  = "#4caf50" if overall >= 80 else "#ff9800" if overall >= 50 else "#f44336"

    med_rows = ""
    for m in stats.get("medications", []):
        pct     = int(m.get("adherence_pct", 0))
        mc      = "#4caf50" if pct >= 80 else "#ff9800" if pct >= 50 else "#f44336"
        name    = str(m.get("medication_id", ""))[:20]
        taken   = m.get("taken", 0)
        total   = m.get("total", 0)
        med_rows += (
            f'<tr><td style="padding:10px 14px;border-bottom:1px solid #f5f5f4;font-size:13px;">'
            f'💊 {escape(name)}</td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid #f5f5f4;">'
            f'<div style="background:{bar_bg};border-radius:4px;height:8px;width:100%;overflow:hidden;">'
            f'<div style="background:{mc};height:100%;width:{pct}%;border-radius:4px;"></div></div>'
            f'</td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid #f5f5f4;font-weight:700;color:{mc};font-size:13px;">{pct}%</td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid #f5f5f4;color:{GRAY};font-size:12px;">{taken}/{total} doses</td>'
            f'</tr>'
        )

    pdf_note = ('<p style="color:{GRAY};font-size:13px;margin-top:16px;">📎 Full report attached as PDF.</p>'
                if pdf_bytes else "")
    body = f"""
<h2 style="color:{GREEN};margin:0 0 6px;">📊 Weekly Adherence Report</h2>
<p style="color:{GRAY};font-size:13px;margin:0 0 24px;">Last {days} days</p>
<div style="text-align:center;padding:28px;background:white;border-radius:12px;
     border:1px solid {BORDER};margin-bottom:24px;">
  <div style="font-size:56px;font-weight:800;color:{color};line-height:1;">{overall}%</div>
  <div style="font-size:16px;font-weight:600;color:{color};margin-top:8px;">{label} Adherence</div>
  <div style="background:{bar_bg};border-radius:6px;height:10px;margin:16px auto 0;max-width:300px;overflow:hidden;">
    <div style="background:{bar_col};height:100%;width:{overall}%;border-radius:6px;"></div>
  </div>
</div>
{f'<table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;border:1px solid {BORDER};"><thead><tr style="background:#f5f5f4;"><th style="padding:10px 14px;text-align:left;font-size:11px;color:{GRAY};text-transform:uppercase;">Medication</th><th style="padding:10px 14px;text-align:left;font-size:11px;color:{GRAY};text-transform:uppercase;">Progress</th><th style="padding:10px 14px;text-align:left;font-size:11px;color:{GRAY};">Rate</th><th style="padding:10px 14px;text-align:left;font-size:11px;color:{GRAY};">Doses</th></tr></thead><tbody>{med_rows}</tbody></table>' if med_rows else ''}
{pdf_note}"""
    plain = f"Weekly Adherence Report: {overall}% ({label}) over {days} days."
    return send_email(
        to, f"📊 Weekly Report: {overall}% Adherence — MediAgent",
        _wrap(_header_tpl("Weekly Adherence Report"), body), plain,
        attachment_bytes=pdf_bytes,
        attachment_name="mediagent-adherence-report.pdf" if pdf_bytes else None,
    )
