"""
Sessions & Chat API — Fully Local Mode
Text: Mistral
Images: LLaVA (Ollama)
PDF: PyMuPDF + Mistral
"""
 
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, field_validator

from backend.services.session_service import (
    create_session,
    get_sessions,
    get_session,
    rename_session,
    delete_session,
)

from backend.agents.chat_agent import chat
from backend.services.llm_service import (
    ask_llm_with_image,
    ask_llm_with_document,
)

log = logging.getLogger("mediagent.api.sessions")
router = APIRouter()


# ─────────────────────────────────────────────
# Input Models
# ─────────────────────────────────────────────


class NewSessionRequest(BaseModel):
    mode: str = "general"
    title: str = "New Chat"
    user_id: str = "demo_user"

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v):
        allowed = {"general", "symptom", "interaction", "prescription"}
        if v not in allowed:
            raise ValueError(f"mode must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("title")
    @classmethod
    def safe_title(cls, v):
        return v.strip()[:120] or "New Chat"


class ChatRequest(BaseModel):
    message: str
    mode: str = "general"

    @field_validator("message")
    @classmethod
    def non_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        return v[:4000]

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, v):
        return (
            v
            if v in {"general", "symptom", "interaction", "prescription"}
            else "general"
        )


class RenameRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def safe_title(cls, v):
        return v.strip()[:120] or "Chat"


# ─────────────────────────────────────────────
# Session CRUD Endpoints
# ─────────────────────────────────────────────


@router.get("/sessions")
def list_sessions(user_id: str = "demo_user"):
    try:
        return get_sessions(user_id)
    except Exception as e:
        log.exception("list_sessions failed")
        raise HTTPException(500, f"Could not load sessions: {e}")


@router.post("/sessions", status_code=201)
def new_session(req: NewSessionRequest):
    try:
        return create_session(user_id=req.user_id, mode=req.mode, title=req.title)
    except Exception as e:
        log.exception("create_session failed")
        raise HTTPException(500, f"Could not create session: {e}")


@router.get("/sessions/{session_id}")
def get_one_session(session_id: str):
    s = get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.patch("/sessions/{session_id}")
def rename(session_id: str, req: RenameRequest):
    s = rename_session(session_id, req.title)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.delete("/sessions/{session_id}")
def remove_session(session_id: str):
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"deleted": True}


# ─────────────────────────────────────────────
# TEXT CHAT ENDPOINT
# ─────────────────────────────────────────────


@router.post("/sessions/{session_id}/chat")
def send_message(session_id: str, req: ChatRequest):
    s = get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")

    try:
        return chat(
            session_id=session_id,
            user_message=req.message,
            mode=req.mode,
        )
    except Exception as e:
        log.exception("chat failed for session %s", session_id)
        raise HTTPException(500, f"Chat error: {e}")


# ─────────────────────────────────────────────
# FILE UPLOAD ENDPOINT (IMAGE + PDF)
# ─────────────────────────────────────────────


@router.post("/sessions/{session_id}/chat/upload")
async def send_message_with_file(
    session_id: str,
    file: UploadFile = File(...),
    message: str = Form(default=""),
    mode: str = Form(default="general"),
):
    """
    Upload image or PDF for analysis.
    - Images → LLaVA
    - PDFs   → PyMuPDF → Mistral
    """

    s = get_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")

    try:
        content = await file.read()
        mime = file.content_type

        if mime and mime.startswith("image/"):
            analysis = ask_llm_with_image(
                message or "Analyze this medical image carefully.",
                content,
            )

        elif mime == "application/pdf":
            analysis = ask_llm_with_document(
                message or "Analyze this medical document and summarize key findings.",
                content,
            )

        else:
            raise HTTPException(415, f"Unsupported file type: {mime}")

        return chat(
            session_id=session_id,
            user_message=f"[Uploaded: {file.filename}] {message}",
            mode=mode,
            prefilled_response=analysis,
        )

    except Exception as e:
        log.exception("Upload processing failed")
        raise HTTPException(500, f"Upload processing failed: {str(e)}")
