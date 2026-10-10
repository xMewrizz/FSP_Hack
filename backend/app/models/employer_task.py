from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile
    from app.models.employer import EmployerProfile
    from app.models.user import User
    from app.models.vacancy import Vacancy


class EmployerTask(Base, TimestampMixin):
    """Короткое задание, составленное работодателем (B-29)."""
    __tablename__ = "employer_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employer_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    vacancy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # auto_check — система проверяет по эталону; manual_review — открытый ответ оценивает работодатель
    task_type: Mapped[str] = mapped_column(String(50), default="manual_review", nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employer: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="tasks")
    vacancy: Mapped["Vacancy | None"] = relationship("Vacancy", back_populates="tasks")
    submissions: Mapped[list["EmployerTaskSubmission"]] = relationship(
        "EmployerTaskSubmission",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="desc(EmployerTaskSubmission.created_at)",
    )


class EmployerTaskSubmission(Base, TimestampMixin):
    """Ответ кандидата на задание работодателя (B-29)."""
    __tablename__ = "employer_task_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employer_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    # graded, pending_review, rejected
    status: Mapped[str] = mapped_column(String(50), default="pending_review", nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped["EmployerTask"] = relationship("EmployerTask", back_populates="submissions")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="task_submissions")
