from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


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


# ── Shared ────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str