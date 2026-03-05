"""
OCR Service — Extract text from prescription images using Tesseract.
From project2.
"""
import re

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_image(image_path: str) -> dict:
    """Extract and clean text from a prescription image."""
    if not OCR_AVAILABLE:
        return {"success": False, "text": "", "error": "OCR dependencies not installed (pytesseract, Pillow)."}

    try:
        image = Image.open(image_path)
        raw_text = pytesseract.image_to_string(image)
        cleaned = clean_prescription_text(raw_text)
        drugs = extract_drug_names(cleaned)
        return {
            "success": True,
            "raw_text": raw_text,
            "cleaned_text": cleaned,
            "detected_drugs": drugs,
        }
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}


def clean_prescription_text(text: str) -> str:
    """Basic cleaning of OCR output."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


COMMON_DRUG_PATTERNS = [
    r"\b(aspirin|warfarin|metformin|ibuprofen|amoxicillin|lisinopril|atorvastatin|omeprazole|"
    r"metoprolol|amlodipine|losartan|levothyroxine|albuterol|gabapentin|sertraline|"
    r"fluoxetine|ciprofloxacin|prednisone|hydrochlorothiazide|tramadol)\b",
]


def extract_drug_names(text: str) -> list[str]:
    """Try to extract drug names from OCR'd prescription text."""
    found = set()
    text_lower = text.lower()
    for pattern in COMMON_DRUG_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        found.update(m.title() for m in matches)
    return sorted(found)
