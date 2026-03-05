"""
Chat Agent — multi-turn medical conversation with full session memory.
Supports prefilled_response for vision/document analysis results.
"""
import json, logging
from backend.services.llm_service import ask_llm_chat
from backend.services.session_service import add_message, get_messages
from backend.triage.rules import assess_triage
from backend.services.interaction_service import check_polypharmacy

log = logging.getLogger("mediagent.agent")

SYSTEM_PROMPTS = {
    "general": (
        "You are MediAgent, a knowledgeable AI medical assistant. Help with symptom understanding, "
        "drug information, medication questions, and general health topics. "
        "Be empathetic, clear, and concise. Recommend professional consultation for serious concerns. "
        "Never definitively diagnose. Flag emergencies immediately with clear action steps."
    ),
    "symptom": (
        "You are MediAgent's Symptom Analyzer. For reported symptoms:\n"
        "1. Assess urgency clearly (Emergency/Urgent/Routine)\n"
        "2. List the most likely causes\n"
        "3. Recommend immediate next steps\n"
        "4. Highlight red flag warning signs\n"
        "5. Suggest follow-up questions if needed\n"
        "Always recommend professional medical consultation."
    ),
    "interaction": (
        "You are MediAgent's Drug Interaction Specialist. For mentioned medications:\n"
        "1. Identify any dangerous interactions\n"
        "2. Rate severity (CRITICAL / HIGH / MEDIUM / LOW)\n"
        "3. Explain the clinical mechanism briefly\n"
        "4. Give practical management recommendations\n"
        "Always advise consulting a pharmacist or prescribing doctor."
    ),
    "prescription": (
        "You are MediAgent's Prescription Analyst. Help users understand their prescriptions:\n"
        "1. Identify all medications and what each treats\n"
        "2. Explain dosing instructions clearly\n"
        "3. Flag potential interactions between listed drugs\n"
        "4. Note key warnings and side effects\n"
        "Always recommend verifying with their pharmacist."
    ),
}

SYMPTOM_KEYWORDS = {
    "pain", "ache", "fever", "cough", "nausea", "headache", "dizzy",
    "tired", "rash", "swelling", "bleeding", "vomit", "hurt", "sore",
    "chest", "breathe", "breathing", "faint", "seizure", "confusion",
}
DRUG_KEYWORDS = {
    "mg", "tablet", "capsule", "dose", "taking", "prescribed",
    "medication", "drug", "pill", "injection", "syrup",
}


def chat(session_id: str, user_message: str, mode: str = "general",
         prefilled_response: str = None) -> dict:
    """
    Process a chat message. If prefilled_response is provided (e.g. from vision
    analysis), skip the LLM call and save the prefilled text directly.
    """
    # Save user message
    try:
        add_message(session_id, "user", user_message)
    except Exception as e:
        log.error("Failed to save user message: %s", e)

    # Run structured checks
    meta = {}
    try:
        text_lower = user_message.lower()
        if mode == "symptom" or any(kw in text_lower for kw in SYMPTOM_KEYWORDS):
            meta["triage"] = assess_triage(user_message)

        if mode == "interaction" or any(kw in text_lower for kw in DRUG_KEYWORDS):
            drugs = _extract_drugs(user_message)
            if len(drugs) >= 2:
                meta["interactions"] = check_polypharmacy(drugs)
    except Exception as e:
        log.warning("Structured check failed: %s", e)

    # Get or generate response
    if prefilled_response:
        response_text = prefilled_response
    else:
        try:
            history = get_messages(session_id)
            system  = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["general"])
            # Build messages list, skip system role entries
            llm_msgs = [
                {"role": m["role"], "content": m["content"]}
                for m in history[-15:]
                if m["role"] in ("user", "assistant")
            ]
            response_text = ask_llm_chat(system, llm_msgs)
        except Exception as e:
            log.exception("LLM call failed")
            response_text = f"⚠️ Unable to process request: {str(e)}"

    # Save assistant response
    try:
        meta_json = json.dumps(meta) if meta else None
        add_message(session_id, "assistant", response_text, meta=meta_json)
    except Exception as e:
        log.error("Failed to save assistant message: %s", e)

    return {
        "response":    response_text,
        "meta":        meta,
        "session_id":  session_id,
        "disclaimer":  "⚠️ AI guidance only — always consult a licensed medical professional.",
    }


def _extract_drugs(text: str) -> list:
    known = [
        "aspirin","ibuprofen","paracetamol","acetaminophen","warfarin",
        "metformin","lisinopril","atorvastatin","omeprazole","amoxicillin",
        "metoprolol","amlodipine","losartan","levothyroxine","albuterol",
        "gabapentin","sertraline","fluoxetine","ciprofloxacin","prednisone",
        "clopidogrel","simvastatin","amiodarone","digoxin","lithium",
        "naproxen","diazepam","alprazolam","hydrochlorothiazide","furosemide",
    ]
    tl = text.lower()
    return [d for d in known if d in tl]
