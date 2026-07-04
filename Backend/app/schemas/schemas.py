from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# ── CV Emotion Analysis ──────────────────────────────────────────

class FrameAnalysisOut(BaseModel):
    face_detected: bool
    top_emotion: str
    top_confidence: float
    eye_contact: bool
    gaze_direction: str


class CVEndOut(BaseModel):
    overall_cv_score: Optional[float]
    eye_contact: Optional[float]
    dominant_emotion: Optional[str]
    behavioral_flags: list[str] = []
    feedback_summary: Optional[str]


# ── Auth ─────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User / Profile ────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    job_title: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None


# ── CV ────────────────────────────────────────────────────────────

class CVUploadOut(BaseModel):
    id: int
    filename: str
    file_size_kb: Optional[float]
    score: Optional[float]
    skills: Optional[list[str]]
    strengths: Optional[list[str]]
    recommendations: Optional[list[str]]
    best_fit_role: Optional[str]
    status: str
    uploaded_at: datetime
    analyzed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CVAnalysisResult(BaseModel):
    score: float
    skills: list[str]
    strengths: list[str]
    recommendations: list[str]


# ── Interview ─────────────────────────────────────────────────────

class InterviewSessionCreate(BaseModel):
    job_title: Optional[str] = None


class InterviewSessionOut(BaseModel):
    id: int
    job_title: Optional[str]
    duration_seconds: Optional[int]
    overall_score: Optional[float]
    confidence_score: Optional[float]
    clarity_score: Optional[float]
    feedback: Optional[str]
    status: str
    created_at: datetime
    analyzed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class InterviewQuestionOut(BaseModel):
    question_index: int
    question_text: str
    answer_transcript: Optional[str]
    score: Optional[float]
    feedback: Optional[str]

    model_config = {"from_attributes": True}


class InterviewSessionDetail(InterviewSessionOut):
    questions: list[InterviewQuestionOut] = []


# ── Chat ──────────────────────────────────────────────────────────

class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    user_message: ChatMessageOut
    ai_message: ChatMessageOut


# ── Answer Evaluation (Sarah) ─────────────────────────────────────

class EvaluateAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(default="", description="Transcribed candidate answer (from Reem's speech-to-text)")
    session_id: Optional[int] = Field(
        default=None, description="If provided with question_index, the score is persisted onto that session"
    )
    question_index: Optional[int] = None


class EvaluateAnswerResponse(BaseModel):
    question: str
    answer: str
    score: float = Field(description="Predicted answer quality, 0-10")
    feedback: str


class SessionFinalizeResponse(BaseModel):
    session_id: int
    overall_score: Optional[float]
    status: str
    questions: list[InterviewQuestionOut] = []


# ── Shared ────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str


# ── Dashboard ─────────────────────────────────────────────────────

class ScoreTrendPoint(BaseModel):
    date: str
    score: float


class SkillSlice(BaseModel):
    name: str
    value: int


class RecentActivityItem(BaseModel):
    date: str
    job_title: str
    score: Optional[float]
    status: str


class DashboardStatsOut(BaseModel):
    greeting_name: str
    cv_score: Optional[float]
    interviews_done: int
    performance: Optional[float]
    jobs_applied: Optional[int]
    score_trend: list[ScoreTrendPoint] = []
    skills_breakdown: list[SkillSlice] = []
    recent_activity: list[RecentActivityItem] = []