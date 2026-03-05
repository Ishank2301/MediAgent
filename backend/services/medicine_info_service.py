"""
Medicine Info Service — drug info lookup via RxNorm + FDA APIs.
Returns dosage, indications, warnings, side effects.
"""
import requests

FDA_BASE = "https://api.fda.gov/drug"
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"


def get_drug_info(drug_name: str) -> dict:
    """Get comprehensive drug info from FDA label + RxNorm."""
    result = {
        "name": drug_name,
        "rxcui": None,
        "brand_names": [],
        "indications": "",
        "dosage": "",
        "warnings": "",
        "side_effects": "",
        "contraindications": "",
        "drug_interactions_text": "",
        "source": "fda_openfda",
    }

    # 1. Get RxCUI
    try:
        r = requests.get(f"{RXNORM_BASE}/rxcui.json?name={drug_name}", timeout=8)
        if r.status_code == 200:
            ids = r.json().get("idGroup", {}).get("rxnormId", [])
            result["rxcui"] = ids[0] if ids else None
    except Exception:
        pass

    # 2. Get FDA label
    try:
        url = f"{FDA_BASE}/label.json?search=openfda.generic_name:{drug_name}&limit=1"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            # Try brand name
            url = f"{FDA_BASE}/label.json?search=openfda.brand_name:{drug_name}&limit=1"
            r = requests.get(url, timeout=10)

        if r.status_code == 200:
            items = r.json().get("results", [])
            if items:
                label = items[0]
                openfda = label.get("openfda", {})

                result["brand_names"] = openfda.get("brand_name", [])[:3]
                result["indications"] = _first(label.get("indications_and_usage", []))
                result["dosage"] = _first(label.get("dosage_and_administration", []))
                result["warnings"] = _first(label.get("warnings", label.get("warnings_and_cautions", [])))
                result["side_effects"] = _first(label.get("adverse_reactions", []))
                result["contraindications"] = _first(label.get("contraindications", []))
                result["drug_interactions_text"] = _first(label.get("drug_interactions", []))
    except Exception as e:
        result["error"] = str(e)

    return result


def _first(lst: list, max_chars: int = 600) -> str:
    if not lst:
        return ""
    text = lst[0] if isinstance(lst, list) else str(lst)
    return text[:max_chars] + ("..." if len(text) > max_chars else "")
