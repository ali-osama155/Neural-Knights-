from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    cv_uploads: Mapped[list["CVUpload"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    interview_sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CVUpload(Base):
    __tablename__ = "cv_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_kb: Mapped[Optional[float]] = mapped_column(Float)

    # AI Analysis results
    score: Mapped[Optional[float]] = mapped_column(Float)          # 0-100
    skills: Mapped[Optional[str]] = mapped_column(Text)            # JSON array
    strengths: Mapped[Optional[str]] = mapped_column(Text)         # JSON array
    recommendations: Mapped[Optional[str]] = mapped_column(Text)   # JSON array
    best_fit_role: Mapped[Optional[str]] = mapped_column(String(255))  # e.g., "Senior Frontend Engineer"
    raw_text: Mapped[Optional[str]] = mapped_column(Text)          # extracted CV text

    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | analyzed | failed
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="cv_uploads")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Session metadata
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    video_path: Mapped[Optional[str]] = mapped_column(String(500))  # stored recording

    # AI evaluation
    overall_score: Mapped[Optional[float]] = mapped_column(Float)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    clarity_score: Mapped[Optional[float]] = mapped_column(Float)
    feedback: Mapped[Optional[str]] = mapped_column(Text)     # JSON detailed feedback
    transcript: Mapped[Optional[str]] = mapped_column(Text)   # whisper transcript
    cv_report: Mapped[Optional[str]] = mapped_column(Text)    # JSON emotion/CV analysis report

    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | analyzed | failed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="interview_sessions")
    questions: Mapped[list["InterviewQuestion"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"), nullable=False)
    question_index: Mapped[int] = mapped_column(Integer)
    question_text: Mapped[str] = mapped_column(Text)
    answer_transcript: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[float]] = mapped_column(Float)
    feedback: Mapped[Optional[str]] = mapped_column(Text)

    session: Mapped["InterviewSession"] = relationship(back_populates="questions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20))   # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="chat_messages")