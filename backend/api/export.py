"""PDF export API routes."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from backend.services.pdf_service import generate_session_report, generate_adherence_report
from backend.services.session_service import get_session
from backend.services.adherence_service import get_adherence_stats, get_medications, get_dose_logs

router = APIRouter()
 

@router.get("/export/session/{session_id}")
def export_session_pdf(session_id: str):
    """Export a chat session as a PDF report."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    try:
        pdf_bytes = generate_session_report(session)
        filename = f"mediagent-session-{session_id[:8]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/export/adherence")
def export_adherence_pdf(user_id: str = "demo_user", days: int = 30):
    """Export a medication adherence report as PDF."""
    try:
        stats = get_adherence_stats(user_id, days)
        medications = get_medications(user_id, active_only=False)
        logs = get_dose_logs(user_id, days)
        pdf_bytes = generate_adherence_report(user_id, stats, medications, logs)
        filename = f"mediagent-adherence-{user_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))
