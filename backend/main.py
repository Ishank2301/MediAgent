"""
MediAgent v5 — FastAPI Application
"""

import logging
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

# ── Configure logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mediagent")

# ── Routers ───────────────────────────────────────────────────────────────────
from backend.api.sessions import router as sessions_router
from backend.api.medical import router as medical_router
from backend.api.prescription import router as prescription_router
from backend.api.history import router as history_router
from backend.api.medicine import router as medicine_router
from backend.api.adherence import router as adherence_router
from backend.api.export import router as export_router
from backend.api.appointments import router as appointments_router
from backend.api.notifications import router as notifications_router
from backend.api.search import router as search_router


# ── Lifespan manager ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MediAgent v5 starting…")

    # Start background scheduler
    scheduler = None
    try:
        from backend.scheduler import start_scheduler

        scheduler = start_scheduler()
        log.info("Scheduler started")
    except Exception as e:
        log.warning("Scheduler not started: %s", e)

    # Log active LLM provider
    try:
        from backend.services.llm_service import get_provider_info

        info = get_provider_info()
        log.info(
            "LLM provider: %s (%s) — vision: %s",
            info["provider"],
            info["model"],
            info["vision"],
        )
    except Exception:
        pass

    yield

    if scheduler:
        try:
            scheduler.shutdown(wait=False)
            log.info("Scheduler stopped")
        except Exception:
            pass

    log.info("MediAgent shutting down")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MediAgent — AI Medical Copilot",
    description=(
        "AI-powered medical assistant: persistent chat, symptom triage, "
        "drug interactions, appointment planning, email/WhatsApp notifications, "
        "medication adherence tracking, image/document upload, live web search."
    ),
    version="5.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS configuration ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(sessions_router, prefix="/api", tags=["Chat"])
app.include_router(medical_router, prefix="/api", tags=["Medical"])
app.include_router(prescription_router, prefix="/api", tags=["Prescription"])
app.include_router(history_router, prefix="/api", tags=["History"])
app.include_router(medicine_router, prefix="/api", tags=["Medicine"])
app.include_router(adherence_router, prefix="/api", tags=["Adherence"])
app.include_router(export_router, prefix="/api", tags=["Export"])
app.include_router(appointments_router, prefix="/api", tags=["Appointments"])
app.include_router(notifications_router, prefix="/api", tags=["Notifications"])
app.include_router(search_router, prefix="/api", tags=["Search"])


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again.",
            "type": type(exc).__name__,
        },
    )


# ── Health & info ─────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    from backend.services.llm_service import get_provider_info

    return {
        "app": "MediAgent",
        "version": "5.0.0",
        "status": "running",
        "llm": get_provider_info(),
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health():
    return {"status": "OK", "version": "5.0.0"}
