"""
CV Service — handles file saving, text extraction, and background processing.
Supports PDF, DOCX, and plain text.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.models import CVUpload
from app.services.ai_service import analyze_cv

logger = logging.getLogger(__name__)
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
    """
    Extract text → call AI → update record.

    IMPORTANT: Background tasks run outside the request lifecycle,
    so we create a fresh DB session instead of reusing the request-scoped one.
    """
    cv_id = cv_record.id
    file_path = cv_record.file_path

    try:
        # Extract text from the uploaded file
        text = extract_text(file_path)
        logger.info(f"Extracted {len(text)} chars from CV id={cv_id}")

        if text.startswith("[Text extraction failed"):
            raise ValueError(f"Text extraction failed for {file_path}: {text}")

        # Run AI analysis (hybrid: local model + API fallback)
        result = await analyze_cv(text)
        logger.info(f"Analysis result for CV id={cv_id}: score={result.get('score')}")

        # Update the record in a NEW session (background task safety)
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(CVUpload).where(CVUpload.id == cv_id)
            db_result = await session.execute(stmt)
            record = db_result.scalar_one_or_none()

            if record is None:
                logger.error(f"CV record id={cv_id} not found in database")
                return cv_record

            record.raw_text = text
            record.score = result.get("score", 0)
            record.skills = json.dumps(result.get("skills", []))
            record.strengths = json.dumps(result.get("strengths", []))
            record.recommendations = json.dumps(result.get("recommendations", []))
            record.best_fit_role = result.get("best_fit_role", "Unknown Role")
            record.status = "analyzed"
            record.analyzed_at = datetime.now(timezone.utc)

            session.add(record)
            await session.commit()
            logger.info(f"CV id={cv_id} marked as analyzed (score={record.score})")
            return record

    except Exception as e:
        logger.error(f"CV processing error for id={cv_id}: {e}", exc_info=True)
        # Mark as failed in a fresh session
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                stmt = select(CVUpload).where(CVUpload.id == cv_id)
                db_result = await session.execute(stmt)
                record = db_result.scalar_one_or_none()
                if record:
                    record.status = "failed"
                    session.add(record)
                    await session.commit()
        except Exception as db_err:
            logger.error(f"Failed to mark CV id={cv_id} as failed: {db_err}")

        return cv_record