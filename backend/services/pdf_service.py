"""
PDF Report Export Service
Generates professional medical reports from sessions, adherence stats, and interaction results.
Uses reportlab per the PDF skill.
"""
import io
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable, KeepTogether)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


SAGE = colors.HexColor("#3a5549")
SAGE_LIGHT = colors.HexColor("#eef2ef")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")
GREEN = colors.HexColor("#16a34a")
LIGHT_GRAY = colors.HexColor("#f5f5f4")
MID_GRAY = colors.HexColor("#78716c")


def _styles():
    base = getSampleStyleSheet()
    custom = {
        "Title": ParagraphStyle("Title", parent=base["Normal"],
            fontSize=22, textColor=SAGE, spaceAfter=4, fontName="Helvetica-Bold"),
        "Subtitle": ParagraphStyle("Subtitle", parent=base["Normal"],
            fontSize=11, textColor=MID_GRAY, spaceAfter=16),
        "H2": ParagraphStyle("H2", parent=base["Normal"],
            fontSize=13, textColor=SAGE, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"),
        "H3": ParagraphStyle("H3", parent=base["Normal"],
            fontSize=11, textColor=colors.HexColor("#1c1917"), spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold"),
        "Body": ParagraphStyle("Body", parent=base["Normal"],
            fontSize=9, textColor=colors.HexColor("#292524"), leading=14, spaceAfter=4),
        "Small": ParagraphStyle("Small", parent=base["Normal"],
            fontSize=8, textColor=MID_GRAY, leading=12),
        "Disclaimer": ParagraphStyle("Disclaimer", parent=base["Normal"],
            fontSize=8, textColor=MID_GRAY, leading=12, borderPad=6,
            backColor=LIGHT_GRAY, borderColor=colors.HexColor("#d6d3d1"),
            borderWidth=0.5, borderRadius=4),
        "Badge": ParagraphStyle("Badge", parent=base["Normal"],
            fontSize=8, fontName="Helvetica-Bold", alignment=TA_CENTER),
    }
    return custom


def _risk_color(level: str) -> colors.Color:
    l = (level or "").upper()
    if l in ("EMERGENCY", "CRITICAL", "HIGH"): return RED
    if l in ("URGENT", "MEDIUM"): return AMBER
    return GREEN


def generate_session_report(session: dict) -> bytes:
    """Generate a PDF from a chat session."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab not installed. Run: pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = _styles()
    story = []

    # Header
    story.append(Paragraph("✚ MediAgent", styles["Title"]))
    story.append(Paragraph(f"Chat Report — {session.get('title','Session')}", styles["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SAGE))
    story.append(Spacer(1, 10))

    # Meta table
    mode = session.get("mode", "general").title()
    created = session.get("created_at", "")[:10] if session.get("created_at") else datetime.now().strftime("%Y-%m-%d")
    meta_data = [
        ["Mode", mode, "Date", created],
        ["Messages", str(len(session.get("messages", []))), "User", session.get("user_id", "demo_user")],
    ]
    meta_table = Table(meta_data, colWidths=[1.1*inch, 2.1*inch, 1.1*inch, 2.1*inch])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), SAGE_LIGHT),
        ("BACKGROUND", (2,0), (2,-1), SAGE_LIGHT),
        ("TEXTCOLOR", (0,0), (0,-1), SAGE),
        ("TEXTCOLOR", (2,0), (2,-1), SAGE),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d6d3d1")),
        ("ROWBACKGROUNDS", (1,0), (1,-1), [colors.white]),
        ("ROWBACKGROUNDS", (3,0), (3,-1), [colors.white]),
        ("PADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    # Messages
    story.append(Paragraph("Conversation", styles["H2"]))
    messages = session.get("messages", [])
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")[:16] if msg.get("timestamp") else ""
        is_user = role == "user"

        # Role badge row
        badge_color = SAGE if is_user else colors.HexColor("#6b7280")
        badge_label = "YOU" if is_user else "MEDIAGENT"
        label_para = Paragraph(badge_label, ParagraphStyle("b", parent=styles["Badge"],
            textColor=colors.white, fontName="Helvetica-Bold", fontSize=7))
        time_para = Paragraph(ts, ParagraphStyle("t", parent=styles["Small"], alignment=TA_RIGHT))
        badge_table = Table([[label_para, time_para]],
                            colWidths=[1*inch, 5.5*inch])
        badge_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,0), badge_color),
            ("PADDING", (0,0), (0,0), 4),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW", (0,0), (-1,-1), 0, colors.white),
        ]))
        story.append(badge_table)

        # Content
        bg = SAGE_LIGHT if is_user else colors.white
        content_lines = content[:2000].split("\n")
        content_paras = []
        for line in content_lines[:40]:
            if line.strip():
                content_paras.append(Paragraph(line[:300], styles["Body"]))

        content_table = Table([[content_paras]], colWidths=[6.5*inch])
        content_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg),
            ("PADDING", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e7e5e4")),
        ]))
        story.append(content_table)
        story.append(Spacer(1, 6))

    # Disclaimer
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d6d3d1")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "⚠ DISCLAIMER: This report is generated by MediAgent, an AI assistant. "
        "It is for informational purposes only and does not constitute medical advice, diagnosis, or treatment. "
        "Always consult a licensed healthcare professional for medical decisions.",
        styles["Disclaimer"]
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated by MediAgent on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
                           styles["Small"]))

    doc.build(story)
    return buf.getvalue()


def generate_adherence_report(user_id: str, stats: dict, medications: list, logs: list) -> bytes:
    """Generate an adherence summary PDF."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab not installed.")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = _styles()
    story = []

    # Header
    story.append(Paragraph("✚ MediAgent", styles["Title"]))
    story.append(Paragraph("Medication Adherence Report", styles["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SAGE))
    story.append(Spacer(1, 10))

    # Overall stats
    overall = stats.get("overall_adherence", 0)
    overall_color = GREEN if overall >= 80 else AMBER if overall >= 50 else RED
    overall_label = "Good" if overall >= 80 else "Fair" if overall >= 50 else "Poor"

    summary_data = [
        ["Overall Adherence", f"{overall}%", "Status", overall_label],
        ["Period", f"{stats.get('days', 30)} days", "User", user_id],
        ["Active Medications", str(len(medications)), "Report Date", datetime.now().strftime("%Y-%m-%d")],
    ]
    summary_table = Table(summary_data, colWidths=[1.5*inch, 1.7*inch, 1.2*inch, 2.1*inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), SAGE_LIGHT),
        ("BACKGROUND", (2,0), (2,-1), SAGE_LIGHT),
        ("TEXTCOLOR", (0,0), (0,-1), SAGE),
        ("TEXTCOLOR", (2,0), (2,-1), SAGE),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d6d3d1")),
        ("PADDING", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR", (1,0), (1,0), overall_color),
        ("FONTNAME", (1,0), (1,0), "Helvetica-Bold"),
        ("FONTSIZE", (1,0), (1,0), 14),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # Per-medication adherence
    story.append(Paragraph("Adherence by Medication", styles["H2"]))
    med_map = {m["id"]: m for m in medications}
    med_stats = stats.get("medications", [])

    if med_stats:
        headers = ["Medication", "Dosage", "Taken", "Missed", "Total", "Adherence", "Status"]
        rows = [headers]
        for ms in med_stats:
            med = med_map.get(ms["medication_id"], {})
            pct = ms["adherence_pct"]
            status_label = "✓ Good" if pct >= 80 else "~ Fair" if pct >= 50 else "✗ Poor"
            rows.append([
                med.get("name", ms["medication_id"][:12]),
                med.get("dosage", "—"),
                str(ms["taken"]),
                str(ms["missed"]),
                str(ms["total"]),
                f"{pct}%",
                status_label,
            ])
        t = Table(rows, colWidths=[1.5*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.8*inch, 1*inch])
        style = TableStyle([
            ("BACKGROUND", (0,0), (-1,0), SAGE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d6d3d1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT_GRAY]),
            ("PADDING", (0,0), (-1,-1), 5),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (2,0), (-1,-1), "CENTER"),
        ])
        # Color adherence column
        for i, ms in enumerate(med_stats, start=1):
            pct = ms["adherence_pct"]
            c = GREEN if pct >= 80 else AMBER if pct >= 50 else RED
            style.add("TEXTCOLOR", (5,i), (5,i), c)
            style.add("FONTNAME", (5,i), (5,i), "Helvetica-Bold")
        t.setStyle(style)
        story.append(t)
    else:
        story.append(Paragraph("No adherence data available yet.", styles["Body"]))

    # Recent dose log
    story.append(Spacer(1, 16))
    story.append(Paragraph("Recent Dose Log", styles["H2"]))
    if logs:
        log_headers = ["Date/Time", "Medication", "Status", "Notes"]
        log_rows = [log_headers]
        for log in logs[:20]:
            med = med_map.get(log["medication_id"], {})
            scheduled = log.get("scheduled_for", "")[:16] if log.get("scheduled_for") else "—"
            status = log.get("status", "—").title()
            log_rows.append([
                scheduled,
                med.get("name", log["medication_id"][:15]),
                status,
                (log.get("notes") or "")[:40],
            ])
        lt = Table(log_rows, colWidths=[1.5*inch, 2*inch, 0.9*inch, 2.1*inch])
        lt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), SAGE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d6d3d1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT_GRAY]),
            ("PADDING", (0,0), (-1,-1), 5),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(lt)
    else:
        story.append(Paragraph("No dose logs recorded yet.", styles["Body"]))

    # Disclaimer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d6d3d1")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "⚠ DISCLAIMER: This adherence report is for personal tracking only and does not constitute medical advice. "
        "Consult your healthcare provider before making any changes to your medication regimen.",
        styles["Disclaimer"]
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated by MediAgent on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC", styles["Small"]))

    doc.build(story)
    return buf.getvalue()
