"""
Drug Interaction Service
Combines project1's simple lookup with project2's real RxNorm API integration.
Also integrates FDA drug label lookups and a risk scoring engine.
"""
import itertools
import requests

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
FDA_BASE = "https://api.fda.gov/drug"

# Hardcoded high-risk pairs as fallback / quick check (from project1, expanded)
HIGH_RISK_PAIRS = [
    ("aspirin", "warfarin", "HIGH", "Increased bleeding risk — antiplatelet + anticoagulant combination."),
    ("aspirin", "clopidogrel", "HIGH", "Dual antiplatelet therapy increases bleeding risk significantly."),
    ("warfarin", "ibuprofen", "HIGH", "NSAIDs increase anticoagulant effect and GI bleeding risk."),
    ("ssri", "maoi", "CRITICAL", "Serotonin syndrome risk — potentially life-threatening."),
    ("metformin", "alcohol", "MEDIUM", "Increased risk of lactic acidosis."),
    ("simvastatin", "amiodarone", "HIGH", "Risk of myopathy and rhabdomyolysis."),
    ("digoxin", "amiodarone", "HIGH", "Digoxin toxicity risk — requires dose reduction."),
    ("lithium", "ibuprofen", "HIGH", "NSAIDs reduce lithium clearance — toxicity risk."),
    ("methotrexate", "nsaids", "HIGH", "NSAIDs reduce methotrexate clearance — toxicity."),
    ("sildenafil", "nitrates", "CRITICAL", "Severe hypotension — potentially fatal combination."),
]

HIGH_RISK_KEYWORDS = ["contraindicated", "fatal", "severe", "black box", "life-threatening", "avoid"]


def get_rxcui(drug_name: str) -> str | None:
    """Look up RxNorm CUI for a drug name."""
    try:
        url = f"{RXNORM_BASE}/rxcui.json?name={drug_name}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            ids = r.json().get("idGroup", {}).get("rxnormId", [])
            return ids[0] if ids else None
    except Exception:
        pass
    return None


def check_rxnorm_interaction(rxcui1: str, rxcui2: str) -> dict:
    """Check RxNorm drug-drug interaction data."""
    try:
        url = f"{RXNORM_BASE}/interaction/list.json?rxcuis={rxcui1}+{rxcui2}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def check_fda_label(drug_name: str) -> dict:
    """Fetch FDA drug label for warnings."""
    try:
        url = f"{FDA_BASE}/label.json?search=openfda.brand_name:{drug_name}&limit=1"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                label = results[0]
                return {
                    "warnings": label.get("warnings", [""])[0][:500] if label.get("warnings") else "",
                    "contraindications": label.get("contraindications", [""])[0][:500] if label.get("contraindications") else "",
                    "drug_interactions": label.get("drug_interactions", [""])[0][:500] if label.get("drug_interactions") else "",
                }
    except Exception:
        pass
    return {}


def calculate_risk_level(interaction_texts: list[str], base_score: int = 0) -> str:
    """Score interactions and return risk level (from project2 risk_engine)."""
    score = base_score
    for text in interaction_texts:
        text_lower = text.lower()
        for kw in HIGH_RISK_KEYWORDS:
            if kw in text_lower:
                score += 3
                break
        # Lighter keywords
        for kw in ["moderate", "caution", "monitor", "adjust"]:
            if kw in text_lower:
                score += 1
                break
    if score >= 6:
        return "HIGH"
    elif score >= 3:
        return "MEDIUM"
    return "LOW"


def quick_check_pair(d1: str, d2: str) -> dict | None:
    """Fast local lookup for known dangerous pairs."""
    d1l, d2l = d1.lower(), d2.lower()
    for entry in HIGH_RISK_PAIRS:
        if (d1l in entry[0] or entry[0] in d1l) and (d2l in entry[1] or entry[1] in d2l):
            return {"severity": entry[2], "description": entry[3], "source": "local_db"}
        if (d2l in entry[0] or entry[0] in d2l) and (d1l in entry[1] or entry[1] in d1l):
            return {"severity": entry[2], "description": entry[3], "source": "local_db"}
    return None


def check_polypharmacy(drug_list: list[str]) -> list[dict]:
    """
    Check all pairwise interactions for a list of drugs.
    Combines local DB + RxNorm API + risk scoring.
    """
    pairs = list(itertools.combinations(drug_list, 2))
    results = []

    for d1, d2 in pairs:
        entry = {"pair": [d1, d2], "interactions": [], "risk_level": "LOW", "source": "none"}

        # 1. Quick local check
        local = quick_check_pair(d1, d2)
        if local:
            entry["interactions"].append(local["description"])
            entry["risk_level"] = local["severity"]
            entry["source"] = "local_db"

        # 2. RxNorm API check
        try:
            r1 = get_rxcui(d1)
            r2 = get_rxcui(d2)
            if r1 and r2:
                api_data = check_rxnorm_interaction(r1, r2)
                full_interaction = api_data.get("fullInteractionTypeGroup", [])
                for group in full_interaction:
                    for item in group.get("fullInteractionType", []):
                        for pair_item in item.get("interactionPair", []):
                            desc = pair_item.get("description", "")
                            sev = pair_item.get("severity", "N/A")
                            if desc:
                                entry["interactions"].append(f"[{sev}] {desc}")
                                entry["source"] = "rxnorm_api"
        except Exception:
            pass

        # 3. Compute overall risk
        if entry["source"] != "local_db" and entry["interactions"]:
            entry["risk_level"] = calculate_risk_level(entry["interactions"])

        results.append(entry)

    return results
