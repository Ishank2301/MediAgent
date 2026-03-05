"""
Triage Rules Engine v2 — weighted scoring with modifiers.
Considers symptom severity, duration, combinations, and risk factors.
"""

# (keyword, score) — higher = more severe
SYMPTOM_SCORES = {
    # Emergency (score >= 10)
    "chest pain": 12, "chest tightness": 11, "heart attack": 15,
    "shortness of breath": 11, "can't breathe": 14, "difficulty breathing": 11,
    "stroke": 15, "facial drooping": 13, "arm weakness": 12, "slurred speech": 12,
    "sudden confusion": 11, "sudden numbness": 11,
    "seizure": 13, "convulsion": 13, "unconscious": 14, "unresponsive": 14,
    "severe bleeding": 12, "coughing blood": 11, "vomiting blood": 12,
    "overdose": 14, "anaphylaxis": 13, "severe allergic reaction": 13,
    "vision loss": 11, "sudden blindness": 13, "severe headache sudden": 12,
    "head injury": 11, "loss of consciousness": 13,
    "suicidal": 15, "self harm": 14,

    # Urgent (score 5–9)
    "high fever": 7, "fever over 39": 8, "fever over 40": 9,
    "blood in stool": 8, "blood in urine": 7,
    "severe pain": 8, "severe abdominal pain": 8, "severe back pain": 7,
    "persistent vomiting": 6, "vomiting for": 6,
    "difficulty swallowing": 6, "swollen leg": 6, "swollen limb": 6,
    "fainting": 7, "passed out": 7, "rapid heartbeat": 6, "palpitations": 6,
    "eye injury": 7, "deep cut": 6, "broken bone": 7, "fracture": 7,
    "dehydration": 6, "kidney pain": 6, "urinary tract infection": 5,
    "ear infection severe": 6, "can't walk": 7, "unable to walk": 7,
    "confusion": 6, "disorientation": 6,

    # Moderate (score 2–4)
    "fever": 3, "high temperature": 3,
    "vomiting": 3, "nausea": 2, "dizziness": 3,
    "headache": 2, "migraine": 3,
    "rash": 2, "skin rash": 2, "hives": 3,
    "diarrhea": 2, "stomach pain": 2, "abdominal pain": 3,
    "cough": 1, "sore throat": 1, "runny nose": 1, "cold": 1,
    "fatigue": 1, "tired": 1, "muscle ache": 1, "back pain": 2,
    "insomnia": 1, "anxiety": 2, "depression": 2,
}

# Words that amplify severity
AMPLIFIERS = {
    "severe": 3, "extreme": 3, "worst": 3, "unbearable": 4,
    "sudden": 2, "sudden onset": 3,
    "cannot": 2, "can't": 2, "unable": 2,
    "spreading": 2, "getting worse": 2, "worsening": 2,
    "for days": 1, "for weeks": 2, "for a week": 2, "chronic": 1,
}

# Risk factors that increase concern
RISK_FACTORS = [
    "diabetic", "diabetes", "heart disease", "heart condition",
    "immunocompromised", "cancer", "elderly", "pregnancy", "pregnant",
    "hiv", "asthma", "copd", "blood thinner", "warfarin",
    "high blood pressure", "hypertension",
]


def assess_triage(text: str) -> dict:
    """
    Score-based triage engine.
    Returns level, score, matched symptoms, risk factors, and action.
    """
    text_lower = text.lower()
    score = 0
    matched = []
    risk_factors_found = []

    # Score symptoms
    for symptom, pts in SYMPTOM_SCORES.items():
        if symptom in text_lower:
            score += pts
            matched.append(symptom)

    # Apply amplifiers
    amplifier_bonus = 0
    for amp, bonus in AMPLIFIERS.items():
        if amp in text_lower:
            amplifier_bonus = max(amplifier_bonus, bonus)
    score += amplifier_bonus

    # Check risk factors
    for rf in RISK_FACTORS:
        if rf in text_lower:
            risk_factors_found.append(rf)
            score += 2  # Each risk factor adds urgency

    # Multi-symptom bonus (combinations are more concerning)
    if len(matched) >= 3:
        score += 2
    if len(matched) >= 5:
        score += 3

    # Determine level
    if score >= 10:
        level = "emergency"
        action = "🚨 Call emergency services (911/999) immediately or go to the nearest Emergency Room."
        color = "red"
    elif score >= 5:
        level = "urgent"
        action = "⚠️ Visit urgent care or your doctor today. Do not wait more than a few hours."
        color = "orange"
    elif score >= 1:
        level = "routine"
        action = "✅ Monitor your symptoms. Schedule a GP visit if they persist or worsen."
        color = "green"
    else:
        level = "routine"
        action = "✅ This appears non-urgent. Rest, stay hydrated, and see your GP if symptoms develop."
        color = "green"

    return {
        "level": level,
        "score": score,
        "matched": matched[:8],
        "risk_factors": risk_factors_found,
        "action": action,
        "color": color,
    }
