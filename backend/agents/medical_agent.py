"""
MediAgent — Unified AI Medical Agent
Combines symptom analysis (project1) with drug interaction intelligence (project2).
"""
from backend.services.llm_service import ask_llm
from backend.triage.rules import assess_triage
from backend.services.interaction_service import check_polypharmacy
from backend.services.memory_service import save_memory

USER_ID = "demo_user"  # Will be replaced with real auth later


def handle_symptom(text: str, age: int = None, sex: str = None, duration_days: int = None, severity: int = None) -> dict:
    """
    Full symptom analysis pipeline:
    1. Triage assessment
    2. LLM explanation
    3. Save to memory
    """
    triage = assess_triage(text)

    # Build enriched prompt
    context_parts = [f"Patient symptoms: {text}"]
    if age:
        context_parts.append(f"Age: {age}")
    if sex:
        context_parts.append(f"Sex: {sex}")
    if duration_days:
        context_parts.append(f"Duration: {duration_days} days")
    if severity:
        context_parts.append(f"Self-reported severity (1-10): {severity}")
    context_parts.append(f"Initial triage assessment: {triage['level'].upper()} — {triage['action']}")

    prompt = "\n".join(context_parts) + "\n\nPlease provide a thorough medical guidance response."
    response = ask_llm(prompt)

    save_memory(
        user_id=USER_ID,
        mode="symptom",
        user_input=text,
        response=response,
        triage_level=triage["level"],
    )

    return {
        "type": "symptom",
        "triage": triage,
        "response": response,
        "disclaimer": "⚠️ This is AI-generated guidance only. Always consult a licensed medical professional for proper diagnosis and treatment.",
    }


def handle_interaction(drugs: list[str]) -> dict:
    """
    Drug interaction analysis pipeline:
    1. RxNorm API lookup for all pairs
    2. Risk scoring
    3. LLM explanation
    4. Save to memory
    """
    if len(drugs) < 2:
        return {"error": "Please provide at least 2 drug names to check interactions."}

    interactions = check_polypharmacy(drugs)

    # Build prompt for LLM
    interaction_summary = []
    max_risk = "LOW"
    risk_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

    for item in interactions:
        pair_str = f"{item['pair'][0]} + {item['pair'][1]}"
        if item["interactions"]:
            interaction_summary.append(f"{pair_str}: {'; '.join(item['interactions'][:2])}")
        else:
            interaction_summary.append(f"{pair_str}: No significant interaction found in database.")

        if risk_order.get(item.get("risk_level", "LOW"), 1) > risk_order.get(max_risk, 1):
            max_risk = item["risk_level"]

    prompt = (
        f"Patient is taking these medications: {', '.join(drugs)}\n\n"
        f"Interaction data found:\n" + "\n".join(interaction_summary) +
        f"\n\nOverall risk level: {max_risk}\n\n"
        "Please provide a clear, detailed explanation of these drug interactions, their clinical significance, "
        "and specific recommendations for the patient and their healthcare provider."
    )

    response = ask_llm(prompt)

    save_memory(
        user_id=USER_ID,
        mode="interaction",
        user_input=", ".join(drugs),
        response=response,
        risk_level=max_risk,
    )

    return {
        "type": "interaction",
        "drugs": drugs,
        "interactions": interactions,
        "overall_risk": max_risk,
        "response": response,
        "disclaimer": "⚠️ This is AI-generated guidance only. Always consult your pharmacist or doctor before changing medications.",
    }


def handle_prescription_analysis(ocr_result: dict) -> dict:
    """
    Analyze a scanned prescription.
    Extracts drugs via OCR then runs interaction check.
    """
    if not ocr_result.get("success"):
        return {"error": ocr_result.get("error", "OCR failed.")}

    drugs = ocr_result.get("detected_drugs", [])
    cleaned_text = ocr_result.get("cleaned_text", "")

    prompt = (
        f"I scanned a prescription. Here is the extracted text:\n{cleaned_text}\n\n"
        f"Detected medications: {', '.join(drugs) if drugs else 'None identified automatically'}\n\n"
        "Please:\n"
        "1. Identify all medications mentioned\n"
        "2. Note any dosing instructions\n"
        "3. Flag any potential concerns\n"
        "4. Summarize what this prescription is treating"
    )

    llm_response = ask_llm(prompt)

    result = {
        "type": "prescription",
        "detected_drugs": drugs,
        "cleaned_text": cleaned_text,
        "llm_analysis": llm_response,
    }

    # If we found drugs, also check interactions
    if len(drugs) >= 2:
        result["interaction_check"] = handle_interaction(drugs)

    save_memory(
        user_id=USER_ID,
        mode="prescription",
        user_input=f"Prescription scan: {', '.join(drugs)}",
        response=llm_response,
    )

    return result
