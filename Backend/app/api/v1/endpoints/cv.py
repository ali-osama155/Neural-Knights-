import json
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
#from app.core.security import get_current_user
from app.models.models import User, CVUpload
from app.schemas.schemas import CVUploadOut, MessageResponse
from app.services.cv_service import save_cv_file, process_cv

router = APIRouter(prefix="/cv", tags=["CV"])


def _serialize(record: CVUpload) -> dict:
    """Convert JSON string fields to lists before returning."""
    data = {
        "id": record.id,
        "filename": record.filename,
        "file_size_kb": record.file_size_kb,
        "score": record.score,
        "skills": json.loads(record.skills) if record.skills else None,
        "strengths": json.loads(record.strengths) if record.strengths else None,
        "recommendations": json.loads(record.recommendations) if record.recommendations else None,
        "best_fit_role": record.best_fit_role,
        "status": record.status,
        "uploaded_at": record.uploaded_at,
        "analyzed_at": record.analyzed_at,
    }
    return data
async def get_dev_user():
    """Simple dev user for testing - no DB required"""
    # Return a minimal User object (mock)
    user = type('User', (), {
        'id': 1,
        'email': 'dev@test.com',
        'full_name': 'Dev User',
    })()
    return user

@router.post("/upload", response_model=CVUploadOut, status_code=201)
async def upload_cv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_dev_user),
):
    """
    Upload a CV (PDF/DOCX/TXT).
    Analysis runs in the background — poll GET /cv/latest for results.
    """
    file_path, size_kb = await save_cv_file(file, current_user.id)

    cv = CVUpload(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size_kb=size_kb,
        status="pending",
    )
    db.add(cv)
    await db.flush()
    await db.commit()

    # Kick off AI analysis without blocking the response
    background_tasks.add_task(process_cv, db, cv)

    return CVUploadOut(**_serialize(cv))


@router.get("/latest", response_model=CVUploadOut)
async def get_latest_cv(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_dev_user),
):
    """Return the most recently uploaded CV for this user."""
    result = await db.execute(
        select(CVUpload)
        .where(CVUpload.user_id == current_user.id)
        .order_by(CVUpload.uploaded_at.desc())
        .limit(1)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="No CV uploaded yet")
    return CVUploadOut(**_serialize(cv))


@router.get("/history", response_model=list[CVUploadOut])
async def get_cv_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_dev_user),
):
    """Return all CV uploads for the current user."""
    result = await db.execute(
        select(CVUpload)
        .where(CVUpload.user_id == current_user.id)
        .order_by(CVUpload.uploaded_at.desc())
    )
    records = result.scalars().all()
    return [CVUploadOut(**_serialize(r)) for r in records]


@router.delete("/{cv_id}", response_model=MessageResponse)
async def delete_cv(
    cv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_dev_user),
):
    """Delete a specific CV upload."""
    result = await db.execute(
        select(CVUpload).where(CVUpload.id == cv_id, CVUpload.user_id == current_user.id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    await db.execute(
        select(CVUpload).where(CVUpload.id == cv_id).delete(synchronize_session=False)
    )
    await db.commit()
    return {"message": "CV deleted"}