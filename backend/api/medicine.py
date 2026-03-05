"""Medicine info lookup API."""
from fastapi import APIRouter, HTTPException
from backend.services.medicine_info_service import get_drug_info
from backend.services.llm_service import ask_llm

router = APIRouter()


@router.get("/medicine/{drug_name}")
def medicine_info(drug_name: str):
    """Get drug info from FDA + RxNorm, with an AI summary."""
    info = get_drug_info(drug_name)

    # Generate AI summary
    prompt = (
        f"Give a concise, patient-friendly summary of the drug: {drug_name}\n\n"
        f"FDA data found:\n"
        f"Indications: {info.get('indications', 'N/A')[:300]}\n"
        f"Warnings: {info.get('warnings', 'N/A')[:300]}\n"
        f"Side effects: {info.get('side_effects', 'N/A')[:300]}\n\n"
        "Summarize in simple language: what it's for, key warnings, and common side effects. "
        "Keep it under 200 words."
    )
    info["ai_summary"] = ask_llm(prompt)
    return info
