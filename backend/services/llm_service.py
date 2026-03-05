import os
import logging
import base64
import requests
import fitz  # PyMuPDF

log = logging.getLogger("mediagent.llm")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
TEXT_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-q4_0")
VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")

TIMEOUT = 90
MAX_PDF_CHARS = 15000  # prevent huge token overflow


SYSTEM_PROMPT = (
    "You are MediAgent, an AI medical assistant. "
    "You are NOT a licensed doctor. "
    "Always recommend professional consultation. "
    "Be structured, medically responsible, and clear. "
    "Use headings and bullet points when helpful. "
    "If situation looks urgent, clearly state emergency action."
)


# ─────────────────────────────────────────────
# TEXT CHAT (MISTRAL)
# ─────────────────────────────────────────────


def ask_llm(prompt: str) -> str:
    payload = {
        "model": TEXT_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser: {prompt}\nAssistant:",
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 800,
        },
    }

    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "⚠️ Ollama is not running. Start it using: ollama serve"

    except requests.exceptions.Timeout:
        return "⚠️ Model response timed out."

    except Exception as e:
        log.exception("Mistral error")
        return f"⚠️ Mistral error: {str(e)}"


# ─────────────────────────────────────────────
# IMAGE ANALYSIS (LLAVA)
# ─────────────────────────────────────────────


def ask_llm_with_image(prompt: str, image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    vision_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Analyze this medical image carefully.\n"
        f"User Question: {prompt}"
    )

    payload = {
        "model": VISION_MODEL,
        "prompt": vision_prompt,
        "images": [b64],
        "stream": False,
        "options": {
            "temperature": 0.3,
        },
    }

    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "⚠️ Ollama vision model not running. Run: ollama pull llava"

    except Exception as e:
        log.exception("Vision error")
        return f"⚠️ Vision model error: {str(e)}"


# ─────────────────────────────────────────────
# PDF ANALYSIS (PYMUPDF + MISTRAL)
# ─────────────────────────────────────────────


def ask_llm_with_document(prompt: str, pdf_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""

        # limit pages to avoid overload
        for page_number, page in enumerate(doc):
            if page_number > 10:  # limit to first 10 pages
                break
            text += page.get_text()

        doc.close()

    except Exception as e:
        log.exception("PDF read error")
        return f"⚠️ Could not read PDF: {str(e)}"

    if not text.strip():
        return "⚠️ No readable text found in PDF."

    trimmed_text = text[:MAX_PDF_CHARS]

    combined_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "The following is extracted text from a medical document:\n\n"
        f"{trimmed_text}\n\n"
        f"User Question: {prompt}\n\n"
        "Summarize key findings, medications, diagnoses, and risks."
    )

    return ask_llm(combined_prompt)


# ─────────────────────────────────────────────
# PROVIDER INFO (for /health endpoint)
# ─────────────────────────────────────────────


def get_provider_info() -> dict:
    return {
        "provider": "ollama",
        "text_model": TEXT_MODEL,
        "vision_model": VISION_MODEL,
        "mode": "fully_local",
    }
