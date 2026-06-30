"""
Interview endpoints.

Flow:
  1. POST /interviews/sessions          — create a new session record
  2. POST /interviews/sessions/{id}/video — upload the 10-min recording
     → background task: transcribe with Whisper → score with AI
  3. GET  /interviews/sessions          — list all past sessions
  4. GET  /interviews/sessions/{id}     — get full detail with per-question scores
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, InterviewSession, InterviewQuestion
from app.schemas.schemas import (
    InterviewSessionCreate,
    InterviewSessionOut,
    InterviewSessionDetail,
    InterviewQuestionOut,
    MessageResponse,
)
from app.services.storage_service import save_video
from app.services.ai_service import analyze_interview

from app.services.question_service import generate_interview_questions
from app.services.tts_service import text_to_speech
from app.services.stt_service import speech_to_text
from fastapi.responses import FileResponse

router = APIRouter(prefix="/interviews", tags=["Interviews"])

# Questions are now generated dynamically from the candidate's role and skills
DEFAULT_QUESTIONS = [
    "Tell me about yourself and your background in software development.",
    "Describe a challenging project you worked on and how you overcame obstacles.",
    "What is your experience with React.js and modern frontend development?",
    "How do you approach debugging a complex bug in production?",
    "Where do you see yourself in the next 3-5 years?",
]


async def _analyze_session(db: AsyncSession, session: InterviewSession) -> None:
    """Background task: run AI analysis on the uploaded video."""
    # In production: call OpenAI Whisper to transcribe the video first.
    # For now, we use a placeholder transcript.
    transcript = speech_to_text(session.video_path) if session.video_path else ""

    result = await analyze_interview(transcript, DEFAULT_QUESTIONS)

    session.overall_score = result.get("overall_score", 0)
    session.confidence_score = result.get("confidence_score", 0)
    session.clarity_score = result.get("clarity_score", 0)
    session.feedback = result.get("feedback", "")
    session.transcript = transcript
    session.status = "analyzed"
    session.analyzed_at = datetime.now(timezone.utc)

    # Save per-question scores
    for q_data in result.get("question_scores", []):
        idx = q_data.get("question_index", 0)
        q_record = InterviewQuestion(
            session_id=session.id,
            question_index=idx,
            question_text=DEFAULT_QUESTIONS[idx] if idx < len(DEFAULT_QUESTIONS) else "",
            score=q_data.get("score"),
            feedback=q_data.get("feedback"),
        )
        db.add(q_record)

    db.add(session)
    await db.commit()


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/sessions", response_model=InterviewSessionOut, status_code=201)
async def create_session(
    body: InterviewSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new interview session record before the recording starts."""
    session = InterviewSession(
        user_id=current_user.id,
        job_title=body.job_title,
        status="pending",
    )
    db.add(session)
    await db.flush()
    return session


@router.post("/sessions/{session_id}/video", response_model=InterviewSessionOut)
async def upload_video(
    session_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    duration_seconds: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload the recorded interview video (webm/mp4).
    AI transcription & scoring runs in the background.
    """
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    video_path = await save_video(file, current_user.id, session_id)
    session.video_path = video_path
    session.duration_seconds = duration_seconds
    db.add(session)

    background_tasks.add_task(_analyze_session, db, session)
    return session


@router.get("/sessions", response_model=list[InterviewSessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all interview sessions for the current user."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=InterviewSessionDetail)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full session detail including per-question scores."""
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    q_result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id)
        .order_by(InterviewQuestion.question_index)
    )
    questions = [InterviewQuestionOut.model_validate(q) for q in q_result.scalars().all()]

    detail = InterviewSessionDetail.model_validate(session)
    detail.questions = questions
    return detail


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    return {"message": "Session deleted"}

# ── Reem's Endpoints ─────────────────────────────────────────────

@router.post("/generate-questions")
async def get_questions(
    job_title: str,
    skills: str,
    #current_user: User = Depends(get_current_user),
):
    """
    Generate interview questions based on role and skills from Ali's CV analysis.
    skills: comma-separated string e.g. "python, tensorflow, deep learning"
    """
    skills_list = [s.strip() for s in skills.split(",")]
    questions = generate_interview_questions(job_title, skills_list)
    return {"questions": questions}


@router.post("/text-to-speech")
async def tts_endpoint(
    text: str,
    #current_user: User = Depends(get_current_user),
):
    """Convert a question to speech audio file."""
    audio_path = text_to_speech(text)
    return FileResponse(audio_path, media_type="audio/mpeg")


@router.post("/speech-to-text")
async def stt_endpoint(
    file: UploadFile = File(...),
    #current_user: User = Depends(get_current_user),
):
    """
    Convert interviewee's audio answer to text.
    Returns transcribed text for Sarah's evaluation.
    """
    audio_path = f"uploads/answer_{file.filename}"
    with open(audio_path, "wb") as f:
        f.write(await file.read())
    
    text = speech_to_text(audio_path)
    return {"text": text}