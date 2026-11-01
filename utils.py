"""Validation, logging, secure file handling and PDF text extraction helpers."""
from __future__ import annotations

import io
import logging
import re
import uuid
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path

import config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9 ()-]{7,20}$")


def setup_logging() -> logging.Logger:
    """Rotating application log. Never log passwords, tokens or document contents."""
    logger = logging.getLogger("healthcarex")
    if logger.handlers:
        return logger
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(config.LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger


# ---- Field validation -----------------------------------------------------
def valid_email(value: str) -> bool:
    value = (value or "").strip()
    return len(value) <= 120 and bool(EMAIL_RE.match(value))


def valid_phone(value: str) -> bool:
    return not value or bool(PHONE_RE.match(value.strip()))


def clean_text(value: str | None, max_len: int = 500) -> str:
    """Trim, collapse whitespace and cap length."""
    return " ".join((value or "").split())[:max_len]


def age_from_dob(dob_iso: str | None) -> int | None:
    if not dob_iso:
        return None
    dob = date.fromisoformat(dob_iso)
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def format_date(iso: str | None) -> str:
    if not iso:
        return "—"
    return date.fromisoformat(iso[:10]).strftime("%d %b %Y")


# ---- Uploads --------------------------------------------------------------
def sniff_extension(data: bytes) -> str | None:
    """Identify the real file type from its signature bytes, not from the file name."""
    if data.startswith(b"%PDF-"):
        return ".pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    return None


def validate_upload(filename: str, data: bytes) -> tuple[bool, str, str]:
    """Return (ok, message, canonical_extension)."""
    ext = Path(filename or "").suffix.lower()
    if ext not in config.ALLOWED_UPLOAD_TYPES:
        return False, "Only PDF, PNG and JPEG files are accepted.", ""
    if not data:
        return False, "The selected file is empty.", ""
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        return False, f"The file is larger than {config.MAX_UPLOAD_MB} MB.", ""
    sniffed = sniff_extension(data)
    expected = ".jpg" if ext == ".jpeg" else ext
    if sniffed is None or sniffed != expected:
        return False, "The file content does not match its extension, so it was rejected.", ""
    return True, "File accepted.", sniffed


def safe_display_name(filename: str) -> str:
    base = Path(filename or "").name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:120].strip()
    return cleaned or "document"


def new_stored_name(ext: str) -> str:
    """Random server-side name; the user's file name is never used on disk."""
    return f"{uuid.uuid4().hex}{ext}"


def _patient_dir(patient_id: int) -> Path:
    folder = config.UPLOAD_DIR / f"patient_{int(patient_id)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _safe_path(patient_id: int, stored_name: str) -> Path | None:
    """Resolve a path and make sure it stays inside this patient's folder."""
    folder = _patient_dir(patient_id).resolve()
    candidate = (folder / Path(stored_name).name).resolve()
    if candidate.parent != folder:
        return None
    return candidate


def save_record_file(patient_id: int, stored_name: str, data: bytes) -> None:
    path = _safe_path(patient_id, stored_name)
    if path is None:
        raise ValueError("Invalid file location.")
    path.write_bytes(data)


def read_record_file(patient_id: int, stored_name: str) -> bytes | None:
    path = _safe_path(patient_id, stored_name)
    if path is None or not path.exists():
        return None
    return path.read_bytes()


def delete_record_file(patient_id: int, stored_name: str) -> None:
    path = _safe_path(patient_id, stored_name)
    if path is not None and path.exists():
        path.unlink()


MIME_BY_EXT = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}


# ---- PDF text ------------------------------------------------------------
def extract_pdf_text(data: bytes, max_pages: int = 20) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = reader.pages[:max_pages]
    return "\n".join((page.extract_text() or "") for page in pages)
