from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile
    from app.models.user import User


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    grade: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="single_choice", nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    correct_answers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class TestSession(Base, TimestampMixin):
    __tablename__ = "test_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    target_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grade_assessments.id", ondelete="CASCADE"),
        index=True, nullable=True,
    )
    skill_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)

    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    skill_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    questions_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    answers_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="test_sessions"
    )


class GradeAssessment(Base, TimestampMixin):
    """Один полный набор обязательных навыков для выбранного грейда."""

    __tablename__ = "grade_assessments"
    __table_args__ = (UniqueConstraint("retake_of_id", name="uq_grade_assessments_retake_of_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retake_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grade_assessments.id", name="fk_grade_assessments_retake_of_id", ondelete="SET NULL"), nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    programming_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    question_codes: Mapped[dict[str, list[str]]] = mapped_column(JSON, nullable=False)
    question_snapshots: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(JSON, nullable=False)
    retake_question_snapshots: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(JSON, nullable=False)
    scoring_policy: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suggested_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
