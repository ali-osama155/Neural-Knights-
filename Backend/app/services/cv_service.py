"""
CV Service — handles file saving and text extraction.
Supports PDF, DOCX, and plain text.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import CVUpload
from app.services.ai_service import analyze_cv

settings = get_settings()
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_cv_file(file: UploadFile, user_id: int) -> tuple[str, float]:
    """Save uploaded file to disk. Returns (file_path, size_kb)."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, DOC, DOCX, or TXT files are accepted",
        )

    dest = UPLOAD_DIR / f"cv_{user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{ext}"
    dest.write_bytes(content)
    return str(dest), round(len(content) / 1024, 1)


def extract_text(file_path: str) -> str:
    """Extract plain text from CV file. Requires pdfminer / python-docx."""
    ext = Path(file_path).suffix.lower()
    try:
        if ext == ".pdf":
            from pdfminer.high_level import extract_text as pdf_extract
            return pdf_extract(file_path)
        elif ext in {".doc", ".docx"}:
            import docx
            doc = docx.Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        else:
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Text extraction failed: {e}]"


async def process_cv(db: AsyncSession, cv_record: CVUpload) -> CVUpload:
    """Extract text → call AI → update record."""
    text = extract_text(cv_record.file_path)
    cv_record.raw_text = text

    result = await analyze_cv(text)

    cv_record.score = result.get("score", 0)
    cv_record.skills = json.dumps(result.get("skills", []))
    cv_record.strengths = json.dumps(result.get("strengths", []))
    cv_record.recommendations = json.dumps(result.get("recommendations", []))
    cv_record.status = "analyzed"
    cv_record.analyzed_at = datetime.now(timezone.utc)

    db.add(cv_record)
    return cv_record