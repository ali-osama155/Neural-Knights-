from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, CVUpload, InterviewSession
from app.schemas.schemas import (
    UserOut,
    ProfileUpdateRequest,
    MessageResponse,
    DashboardStatsOut,
    ScoreTrendPoint,
    SkillSlice,
    RecentActivityItem,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's profile fields."""
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.job_title is not None:
        current_user.job_title = body.job_title
    if body.bio is not None:
        current_user.bio = body.bio
    db.add(current_user)
    return current_user


@router.get("/dashboard", response_model=DashboardStatsOut)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Real dashboard statistics for the authenticated user, replacing the
    previously hardcoded frontend values.

      - cv_score: score of the most recently uploaded CV.
      - interviews_done: count of interview sessions with status == "analyzed"
        (i.e. actually completed & scored) for this user.
      - performance: average overall_score across this user's analyzed
        interview sessions, expressed as a 0-100 percentage. The per-question
        BERT scorer produces 0-10 scores, and finalize_session() averages
        those into InterviewSession.overall_score on that same 0-10 scale,
        so we scale by 10 here for a percentage-style figure.
      - jobs_applied: there's no job-application tracking table in this
        schema yet, so this is returned as null ("N/A" in the UI) instead of
        a fabricated number.
      - score_trend / skills_breakdown / recent_activity: feed the dashboard
        charts/table from real CV uploads and interview sessions instead of
        the previous static mock arrays.
    """
    # Latest CV
    cv_result = await db.execute(
        select(CVUpload)
        .where(CVUpload.user_id == current_user.id)
        .order_by(CVUpload.uploaded_at.desc())
    )
    cv_uploads = list(cv_result.scalars().all())
    latest_cv = cv_uploads[0] if cv_uploads else None

    # All interview sessions
    sess_result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    )
    sessions = list(sess_result.scalars().all())
    analyzed_sessions = [s for s in sessions if s.status == "analyzed" and s.overall_score is not None]

    interviews_done = len(analyzed_sessions)
    if analyzed_sessions:
        avg_score_0_to_10 = sum(s.overall_score for s in analyzed_sessions) / len(analyzed_sessions)
        performance = round(min(100.0, max(0.0, avg_score_0_to_10 * 10)), 1)
    else:
        performance = None

    # Score trend — CV scores over time (most recent 10, oldest first)
    score_trend = [
        ScoreTrendPoint(date=cv.uploaded_at.strftime("%b %d"), score=cv.score)
        for cv in reversed(cv_uploads[:10])
        if cv.score is not None
    ]

    # Skills breakdown — from the latest CV's detected skills
    skills_breakdown: list[SkillSlice] = []
    if latest_cv and latest_cv.skills:
        try:
            skills_list = json.loads(latest_cv.skills)
            skills_breakdown = [SkillSlice(name=s, value=1) for s in skills_list[:8]]
        except (json.JSONDecodeError, TypeError):
            pass

    # Recent activity — latest interview sessions
    #
    # NOTE: "analyzed" only means the scoring pipeline finished processing
    # the session — it says nothing about how well the candidate did. We
    # previously mapped analyzed -> "Passed" unconditionally, which is why
    # a session scored at 11.9% was still shown as "Passed". The Passed/
    # Failed label must instead be derived from the actual score against a
    # passing threshold; pipeline status is only used to detect
    # pending/failed *processing* (not candidate performance).
    PASSING_SCORE_THRESHOLD = 60.0  # percentage; see Issue #4 discussion

    def _activity_status(session: InterviewSession) -> str:
        if session.status == "pending":
            return "Pending"
        if session.status == "failed":
            return "Failed"
        if session.status == "analyzed":
            if session.overall_score is None:
                return "Pending"
            score_pct = session.overall_score * 10
            return "Passed" if score_pct >= PASSING_SCORE_THRESHOLD else "Failed"
        return session.status

    recent_activity = [
        RecentActivityItem(
            date=s.created_at.strftime("%b %d"),
            job_title=s.job_title or "General Interview",
            score=round(s.overall_score * 10, 1) if s.overall_score is not None else None,
            status=_activity_status(s),
        )
        for s in sessions[:6]
    ]

    return DashboardStatsOut(
        greeting_name=current_user.full_name.split(" ")[0] if current_user.full_name else current_user.email.split("@")[0],
        cv_score=latest_cv.score if latest_cv else None,
        interviews_done=interviews_done,
        performance=performance,
        jobs_applied=None,  # not implemented in this schema yet — frontend shows "N/A"
        score_trend=score_trend,
        skills_breakdown=skills_breakdown,
        recent_activity=recent_activity,
    )


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete account by deactivating it."""
    current_user.is_active = False
    db.add(current_user)
    return {"message": "Account deactivated"}