"""Medical API routes — symptom analysis & drug interactions."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from backend.agents.medical_agent import handle_symptom, handle_interaction

router = APIRouter()


class SymptomRequest(BaseModel):
    text: str
    age: Optional[int] = None
    sex: Optional[str] = None
    duration_days: Optional[int] = None
    severity: Optional[int] = None


class InteractionRequest(BaseModel):
    drugs: List[str]


@router.post("/symptom")
async def analyze_symptom(req: SymptomRequest):
    return handle_symptom(
        text=req.text,
        age=req.age,
        sex=req.sex,
        duration_days=req.duration_days,
        severity=req.severity,
    )


@router.post("/interaction")
async def check_interaction(req: InteractionRequest):
    return handle_interaction(drugs=req.drugs)
