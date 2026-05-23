import base64
import logging
import os

import fitz  # PyMuPDF
import requests

log = logging.getLogger("mediagent.llm")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_API_BASE = os.getenv(
    "GEMINI_API_BASE",
    "https://generativelanguage.googleapis.com/v1beta",
).rstrip("/")

TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "35"))
MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2500"))
MAX_PDF_CHARS = int(os.getenv("MAX_PDF_CHARS", "15000"))

SYSTEM_PROMPT = (
    "You are MediAgent, an AI medical assistant. You are not a licensed doctor, but you provide detailed, comprehensive, "
    "evidence-based medical guidance. When responding to symptoms or medical questions:\n"
    "1. Provide DETAILED explanations - cover multiple aspects and perspectives\n"
    "2. List potential causes ranked by likelihood\n"
    "3. Explain each condition clearly in plain language\n"
    "4. Provide specific self-care advice and warning signs\n"
    "5. Always mention when urgent/emergency care is needed (red flags)\n"
    "6. Recommend consultation with specific types of healthcare professionals\n"
    "7. Do NOT diagnose definitively - emphasize these are possibilities, not diagnoses\n"
    "8. Be thorough and informative while remaining medically responsible."
)


def ask_llm(prompt: str) -> str:
    return ask_llm_chat(SYSTEM_PROMPT, [{"role": "user", "content": prompt}])


def ask_llm_chat(system_prompt: str, messages: list[dict]) -> str:
    contents = _build_contents(messages)
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.35,
            "topP": 0.9,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }
    return _generate_content(payload)


def ask_llm_with_image(prompt: str, image_bytes: bytes) -> str:
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": _detect_image_mime(image_bytes),
                            "data": base64.b64encode(image_bytes).decode("utf-8"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }
    return _generate_content(payload)


def ask_llm_with_document(prompt: str, pdf_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page_number, page in enumerate(doc):
            if page_number >= 10:
                break
            text += page.get_text()
        doc.close()
    except Exception as e:
        log.exception("PDF read error")
        return f"Could not read PDF: {str(e)}"

    if not text.strip():
        return "No readable text found in PDF."

    trimmed_text = text[:MAX_PDF_CHARS]
    combined_prompt = (
        "The following is extracted text from a medical document:\n\n"
        f"{trimmed_text}\n\n"
        f"User question: {prompt}\n\n"
        "Summarize key findings, medications, diagnoses, risks, and recommended follow-up."
    )
    return ask_llm(combined_prompt)


def get_provider_info() -> dict:
    return {
        "provider": "gemini",
        "model": GEMINI_MODEL,
        "vision": GEMINI_MODEL,
        "mode": "cloud_api",
        "configured": bool(GEMINI_API_KEY),
    }


def _generate_content(payload: dict) -> str:
    if not GEMINI_API_KEY:
        return (
            "Gemini is not configured. Add GEMINI_API_KEY to your backend environment "
            "and restart the server."
        )

    url = f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent"
    try:
        response = requests.post(
            url,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return _extract_text(data) or "Gemini returned an empty response."
    except requests.exceptions.Timeout:
        return "Gemini response timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        details = _safe_error_detail(e.response)
        log.warning("Gemini HTTP error: %s", details)
        return f"Gemini API error: {details}"
    except Exception as e:
        log.exception("Gemini request failed")
        return f"Gemini request failed: {str(e)}"


def _build_contents(messages: list[dict]) -> list[dict]:
    contents = []
    for message in messages[-10:]:
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        role = "model" if message.get("role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": content[:4000]}]})
    return contents or [{"role": "user", "parts": [{"text": "Hello"}]}]


def _extract_text(data: dict) -> str:
    parts = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _safe_error_detail(response) -> str:
    if response is None:
        return "unknown HTTP error"
    try:
        data = response.json()
        return data.get("error", {}).get("message") or str(data)
    except Exception:
        return response.text[:500]


def _detect_image_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"
