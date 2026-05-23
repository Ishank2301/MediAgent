"""MediAgent FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("mediagent")

from backend.api.adherence import router as adherence_router
from backend.api.appointments import router as appointments_router
from backend.api.export import router as export_router
from backend.api.history import router as history_router
from backend.api.medical import router as medical_router
from backend.api.medicine import router as medicine_router
from backend.api.notifications import router as notifications_router
from backend.api.prescription import router as prescription_router
from backend.api.search import router as search_router
from backend.api.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MediAgent starting")

    scheduler = None
    try:
        from backend.scheduler import start_scheduler

        scheduler = start_scheduler()
        log.info("Scheduler started")
    except Exception as e:
        log.warning("Scheduler not started: %s", e)

    try:
        from backend.services.llm_service import get_provider_info

        info = get_provider_info()
        log.info(
            "LLM provider: %s (%s) - vision: %s - configured: %s",
            info.get("provider"),
            info.get("model"),
            info.get("vision"),
            info.get("configured"),
        )
    except Exception as e:
        log.warning("Could not read LLM provider info: %s", e)

    yield

    if scheduler:
        try:
            scheduler.shutdown(wait=False)
            log.info("Scheduler stopped")
        except Exception:
            pass

    log.info("MediAgent shutting down")


app = FastAPI(
    title="MediAgent - AI Medical Copilot",
    description=(
        "AI-powered medical assistant: persistent chat, symptom triage, "
        "drug interactions, appointment planning, notifications, "
        "medication adherence tracking, image/document upload, and live web search."
    ),
    version="5.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
