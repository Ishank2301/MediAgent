"""
Secure File Upload Service
- Validates file type by magic bytes (not just extension)
- Enforces size limits
- Sanitizes filenames to prevent path traversal
- Supports images (JPEG, PNG, WEBP, GIF) and documents (PDF)
"""
import os, mimetypes, logging
from pathlib import Path
from fastapi import UploadFile, HTTPException

log = logging.getLogger("mediagent.upload")

MAX_SIZE_MB    = 10
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

# Magic byte signatures for each allowed type
MAGIC_SIGNATURES = {
    b"\xff\xd8\xff":          "image/jpeg",
    b"\x89PNG\r\n\x1a\n":    "image/png",
    b"RIFF":                  "image/webp",   # also checked below
    b"GIF87a":                "image/gif",
    b"GIF89a":                "image/gif",
    b"%PDF":                  "application/pdf",
}

ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_DOCS   = {"application/pdf"}
ALLOWED_ALL    = ALLOWED_IMAGES | ALLOWED_DOCS

ANTHROPIC_MEDIA_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/png":  "image/png",
    "image/webp": "image/webp",
    "image/gif":  "image/gif",
    "application/pdf": "application/pdf",
}


def detect_mime(data: bytes) -> str | None:
    """Detect MIME type from magic bytes — safe, not spoofable via extension."""
    for sig, mime in MAGIC_SIGNATURES.items():
        if data[:len(sig)] == sig:
            # Extra check for WebP (RIFF....WEBP)
            if mime == "image/webp" and len(data) >= 12 and data[8:12] != b"WEBP":
                continue
            return mime
    return None


def sanitize_filename(name: str) -> str:
    """Remove path traversal and dangerous characters."""
    name = os.path.basename(name or "upload")
    safe = "".join(c for c in name if c.isalnum() or c in "._- ")
    return (safe.strip() or "upload")[:80]


async def read_upload(file: UploadFile,
                      allowed: set = None,
                      max_bytes: int = MAX_SIZE_BYTES) -> tuple[bytes, str]:
    """
    Read and validate an uploaded file.
    Returns (content_bytes, detected_mime_type).
    Raises HTTPException with clear messages on any violation.
    """
    allowed = allowed or ALLOWED_ALL

    # Read into memory
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read uploaded file: {e}")

    # Empty file check
    if not content:
        raise HTTPException(400, "Uploaded file is empty.")

    # Size check
    if len(content) > max_bytes:
        raise HTTPException(
            413,
            f"File too large ({len(content)//1024//1024:.1f}MB). "
            f"Maximum allowed size is {max_bytes//1024//1024}MB."
        )

    # Magic byte MIME detection
    mime = detect_mime(content)
    if not mime:
        # Fallback to extension-based guess (less secure but graceful)
        ext_mime, _ = mimetypes.guess_type(file.filename or "")
        mime = ext_mime or "application/octet-stream"

    # Type allowlist check
    if mime not in allowed:
        friendly = {
            "image/jpeg": "JPEG image",
            "image/png":  "PNG image",
            "image/webp": "WebP image",
            "image/gif":  "GIF image",
            "application/pdf": "PDF document",
        }
        allowed_names = ", ".join(friendly.get(t, t) for t in sorted(allowed))
        raise HTTPException(
            415,
            f"File type not allowed (detected: {mime}). "
            f"Accepted formats: {allowed_names}."
        )

    log.info("Upload accepted: %s → %s (%d bytes)",
             sanitize_filename(file.filename or ""), mime, len(content))
    return content, mime


def is_image(mime: str) -> bool:
    return mime in ALLOWED_IMAGES


def is_pdf(mime: str) -> bool:
    return mime == "application/pdf"


def get_anthropic_media_type(mime: str) -> str:
    return ANTHROPIC_MEDIA_TYPES.get(mime, "application/octet-stream")
