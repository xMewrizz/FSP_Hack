from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, LargeBinary, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, utc_now

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
    specialization: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    min_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    max_grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evaluation_criteria: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    resource_links: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_platform_task: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employer: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="tasks")
    vacancy: Mapped["Vacancy | None"] = relationship("Vacancy", back_populates="tasks")
    submissions: Mapped[list["EmployerTaskSubmission"]] = relationship(
        "EmployerTaskSubmission",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="desc(EmployerTaskSubmission.created_at)",
    )
    attachments: Mapped[list["TaskAttachment"]] = relationship(
        "TaskAttachment",
        back_populates="task",
        cascade="all, delete-orphan",
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
    answer_links: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contact_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped["EmployerTask"] = relationship("EmployerTask", back_populates="submissions")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="task_submissions")
    attachments: Mapped[list["TaskAttachment"]] = relationship(
        "TaskAttachment",
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class EmployerTaskMessage(Base):
    """Private in-app message about a submitted employer task."""
    __tablename__ = "employer_task_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employer_task_submissions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employer_tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employer_task_submissions.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    task: Mapped["EmployerTask | None"] = relationship("EmployerTask", back_populates="attachments")
    submission: Mapped["EmployerTaskSubmission | None"] = relationship(
        "EmployerTaskSubmission",
        back_populates="attachments",
    )
