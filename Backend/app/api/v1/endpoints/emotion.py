"""
emotion.py
──────────
Real-time CV analysis endpoints — integrates cv_module into the FastAPI backend.

Three endpoints added to /interviews/:
  POST /interviews/sessions/{id}/cv-start
      Call when the recording begins. Starts the cv_module session.

  POST /interviews/sessions/{id}/analyze-frame
      Called every ~350ms from Interview.jsx.
      Receives one base64 JPEG frame, returns face/emotion/gaze data.

  POST /interviews/sessions/{id}/cv-end
      Call when the candidate ends the session.
      Aggregates all frames → report → saves to InterviewSession.cv_report.
"""

import base64
import json
import sys
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, InterviewSession
from app.schemas.schemas import FrameAnalysisOut, CVEndOut

# ── Import cv_module ──────────────────────────────────────────────────────────
# cv_module sits at the repo root (sibling of Backend/).
# This path resolves correctly whether you run uvicorn from Backend/ or root.
# emotion.py lives at Backend/app/api/v1/endpoints/emotion.py
# cv_module lives at Neural-Knights-/cv_module/
# So we need 5 dirname calls to get from emotion.py up to Neural-Knights-/
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from cv_module.cv_pipeline import CVPipeline
    from cv_module.feedback_generator import generate_session_feedback, generate_question_feedback
    _CV_AVAILABLE = True
except ImportError as e:
    print(f"[emotion] WARNING: cv_module not available — {e}")
    _CV_AVAILABLE = False

router = APIRouter(prefix="/interviews", tags=["Emotion CV"])

# ── Single shared CVPipeline (camera_index=None — browser owns camera) ────────
_cv: "CVPipeline | None" = None

def get_cv() -> "CVPipeline":
    global _cv
    if not _CV_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="CV module not available. Make sure cv_module/ is at the repo root "
                   "and the model file is at cv_module/models/fer_raf_combined_final.keras"
        )
    if _cv is None:
        _cv = CVPipeline(camera_index=None, enable_face_mesh=True)
    return _cv


# ── Helper ────────────────────────────────────────────────────────────────────
async def _get_session_or_404(
    session_id: int,
    current_user: User,
    db: AsyncSession,
) -> InterviewSession:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── POST /interviews/sessions/{id}/cv-start ───────────────────────────────────
@router.post("/sessions/{session_id}/cv-start")
async def cv_start(
    session_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Call this when the recording begins.
    Body: { "question_text": "Tell me about yourself." }  (optional)
    """
    await _get_session_or_404(session_id, current_user, db)

    cv = get_cv()
    cv.start_session()
    cv.start_question(
        question_id=session_id,
        question_text=body.get("question_text", "Full interview session"),
    )
    print(f"[cv-start] session_id={session_id} recording={cv._recording}")
    return {"status": "recording"}


# ── POST /interviews/sessions/{id}/cv-next-question ───────────────────────────
@router.post("/sessions/{session_id}/cv-next-question")
async def cv_next_question(
    session_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Call before questions 2, 3, 4... (NOT question 1 — cv-start already
    handles question 1). Starts tracking for the new question WITHOUT
    resetting the whole session.
    Body: { "question_text": "..." }
    """
    await _get_session_or_404(session_id, current_user, db)
    cv = get_cv()
    cv.start_question(
        question_id=session_id,
        question_text=body.get("question_text", ""),
    )
    print(f"[cv-next-question] session_id={session_id}")
    return {"status": "recording"}


# ── POST /interviews/sessions/{id}/analyze-frame ──────────────────────────────
@router.post("/sessions/{session_id}/analyze-frame", response_model=FrameAnalysisOut)
async def analyze_frame(
    session_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called every ~350ms from Interview.jsx while the candidate is answering.
    Body: { "frame": "data:image/jpeg;base64,..." }
    """
    await _get_session_or_404(session_id, current_user, db)

    data_url = body.get("frame", "")
    if not data_url:
        raise HTTPException(status_code=400, detail='Missing "frame" field')

    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        image_bytes = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image")

    cv = get_cv()
    result = cv.analyze_frame(image_bytes)
    print(f"[debug] eye={result.get('eye_contact')} gaze={result.get('gaze_direction')}")

    print(
        f"[analyze-frame] face={result.get('face_detected')} "
        f"emotion={result.get('top_emotion')} recording={cv._recording}"
    )
    return FrameAnalysisOut(**result)


# ── POST /interviews/sessions/{id}/cv-question-feedback ───────────────────────
@router.post("/sessions/{session_id}/cv-question-feedback")
async def cv_question_feedback(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Call immediately after the candidate submits an answer.
    Ends tracking for THIS question only (not the whole session) and
    returns readable feedback for just this question.
    """
    await _get_session_or_404(session_id, current_user, db)
    cv = get_cv()

    q_report = cv.end_question()
    q_feedback = generate_question_feedback(q_report)

    print(f"[cv-question-feedback] session_id={session_id} eye_contact={q_report.get('eye_contact_pct')}")
    return q_feedback


# ── POST /interviews/sessions/{id}/cv-end ─────────────────────────────────────
@router.post("/sessions/{session_id}/cv-end", response_model=CVEndOut)
async def cv_end(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Call this when the candidate ends the interview.
    Aggregates all recorded frames into a report and saves it to the DB.
    """
    session = await _get_session_or_404(session_id, current_user, db)

    cv = get_cv()
    q_report = cv.end_question()
    summary  = cv.end_session()
    feedback = generate_session_feedback(summary)

    # Save full CV report as JSON into the session row
    session.cv_report = json.dumps({
        "question_report" : q_report,
        "session_summary" : summary,
        "feedback"        : feedback,
        "overall_cv_score": feedback.get("overall_cv_score"),
    })

    # Also populate the existing score column so Dashboard picks it up
    if session.confidence_score is None:
        session.confidence_score = feedback.get("overall_cv_score")

    db.add(session)
    await db.commit()

    print(f"[cv-end] session_id={session_id} score={feedback.get('overall_cv_score')}")

    return CVEndOut(
        overall_cv_score  = feedback.get("overall_cv_score"),
        eye_contact       = q_report.get("eye_contact_pct"),
        dominant_emotion  = q_report.get("dominant_emotion"),
        behavioral_flags  = q_report.get("behavioral_flags", []),
        feedback_summary  = feedback.get("overall_summary"),
    )
