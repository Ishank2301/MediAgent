"""
Background Scheduler — automatic reminders & reports.
Uses APScheduler (lightweight, no Redis needed).

Jobs:
  • Every hour  — check for appointments due in 24h → send reminders
  • Every hour  — check for missed medication doses → send alerts
  • Every Monday 8am — send weekly adherence report to all users
  • Every day 7am — send today's medication schedule

Install: pip install apscheduler
"""
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("mediagent.scheduler")


def start_scheduler(app=None):
    """Attach the scheduler to the FastAPI app lifecycle."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed. Run: pip install apscheduler")
        return None

    scheduler = BackgroundScheduler(timezone="UTC")

    # ── Job 1: Appointment reminders every hour ───────────────────────────────
    def check_appointment_reminders():
        try:
            from backend.services.appointment_service import get_due_reminders, mark_reminder_sent
            from backend.services.email_service import send_appointment_reminder
            from backend.services.whatsapp_service import send_appointment_whatsapp
            due = get_due_reminders(hours_ahead=24)
            for apt in due:
                if apt.get("email"):
                    send_appointment_reminder(apt["email"], apt)
                if apt.get("phone"):
                    send_appointment_whatsapp(apt["phone"], apt)
                mark_reminder_sent(apt["id"])
                logger.info(f"Appointment reminder sent: {apt['title']}")
        except Exception as e:
            logger.error(f"Appointment reminder job error: {e}")

    # ── Job 2: Daily medication reminders at 7:00 AM UTC ─────────────────────
    def send_daily_med_reminders():
        """
        In a real multi-user system this would query all users.
        For the hackathon demo, reads from REMINDER_EMAIL and REMINDER_PHONE env vars.
        """
        try:
            from backend.services.adherence_service import get_todays_schedule
            from backend.services.email_service import send_medication_reminder
            from backend.services.whatsapp_service import send_medication_whatsapp

            email = os.getenv("REMINDER_EMAIL", "")
            phone = os.getenv("REMINDER_PHONE", "")
            if not email and not phone:
                return  # Nothing configured

            schedule = get_todays_schedule("demo_user")
            pending = [s for s in schedule if not s.get("taken")]
            if not pending:
                return

            if email:
                send_medication_reminder(email, pending)
            if phone:
                send_medication_whatsapp(phone, pending)
            logger.info(f"Daily med reminders sent: {len(pending)} medications")
        except Exception as e:
            logger.error(f"Daily med reminder job error: {e}")

    # ── Job 3: Weekly adherence report every Monday 8 AM UTC ─────────────────
    def send_weekly_report():
        try:
            from backend.services.adherence_service import get_adherence_stats, get_medications, get_dose_logs
            from backend.services.email_service import send_weekly_adherence_report
            from backend.services.whatsapp_service import send_weekly_summary_whatsapp
            from backend.services.pdf_service import generate_adherence_report

            email = os.getenv("REMINDER_EMAIL", "")
            phone = os.getenv("REMINDER_PHONE", "")
            if not email and not phone:
                return

            stats = get_adherence_stats("demo_user", days=7)
            pdf_bytes = None
            try:
                meds = get_medications("demo_user", active_only=False)
                logs = get_dose_logs("demo_user", 7)
                pdf_bytes = generate_adherence_report("demo_user", stats, meds, logs)
            except Exception:
                pass

            if email:
                send_weekly_adherence_report(email, stats, pdf_bytes)
            if phone:
                send_weekly_summary_whatsapp(phone, stats)
            logger.info("Weekly adherence report sent")
        except Exception as e:
            logger.error(f"Weekly report job error: {e}")

    # ── Register jobs ─────────────────────────────────────────────────────────
    scheduler.add_job(check_appointment_reminders, "interval", hours=1,
                      id="appointment_reminders", replace_existing=True)

    scheduler.add_job(send_daily_med_reminders,
                      CronTrigger(hour=7, minute=0),
                      id="daily_med_reminders", replace_existing=True)

    scheduler.add_job(send_weekly_report,
                      CronTrigger(day_of_week="mon", hour=8, minute=0),
                      id="weekly_report", replace_existing=True)

    scheduler.start()
    logger.info("✅ MediAgent scheduler started (3 jobs)")
    return scheduler
