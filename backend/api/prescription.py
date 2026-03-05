"""Prescription scanning API route."""
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List
from backend.services.ocr_service import extract_text_from_image
from backend.agents.medical_agent import handle_prescription_analysis, handle_interaction

router = APIRouter()


@router.post("/prescription/scan")
async def scan_prescription(file: UploadFile = File(...)):
    """Upload a prescription image for OCR + AI analysis."""
    allowed = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"File type {file.content_type} not supported. Use JPEG, PNG, WEBP, or TIFF.")

    # Save temp file
    suffix = "." + file.filename.split(".")[-1] if "." in file.filename else ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        ocr_result = extract_text_from_image(tmp_path)
        result = handle_prescription_analysis(ocr_result)
    finally:
        os.unlink(tmp_path)

    return result


class ManualDrugsRequest(BaseModel):
    drugs: List[str]


@router.post("/prescription/analyze")
async def analyze_drugs(req: ManualDrugsRequest):
    """Analyze a manually entered list of drugs (no OCR needed)."""
    return handle_interaction(drugs=req.drugs)
