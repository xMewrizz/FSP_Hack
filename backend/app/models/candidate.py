from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate_activity import CandidateActivity
    from app.models.employer_task import EmployerTaskSubmission
    from app.models.fsp import FSPAchievement
    from app.models.invitation import Invitation
    from app.models.test import TestSession
    from app.models.user import User
    from app.models.vacancy import VacancyApplication


class CandidateProfile(Base, TimestampMixin):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    specialization: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    programming_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    declared_grade: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    verified_grade: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    verified_specialization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_grade_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    work_format: Mapped[str | None] = mapped_column(String(50), default="remote", nullable=True)
    salary_expectation: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_tax_type: Mapped[str] = mapped_column(String(20), default="gross", nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    fsp_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    fsp_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    agreed_152_fz: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agreed_152_fz_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agreed_publication: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agreed_publication_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agreed_osint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agreed_osint_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    visibility_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mentor_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")
    fsp_achievements: Mapped[list["FSPAchievement"]] = relationship(
        "FSPAchievement",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    test_sessions: Mapped[list["TestSession"]] = relationship(
        "TestSession",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
        order_by="desc(TestSession.created_at)",
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(Invitation.created_at)",
    )
    applications: Mapped[list["VacancyApplication"]] = relationship(
        "VacancyApplication",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(VacancyApplication.created_at)",
    )
    task_submissions: Mapped[list["EmployerTaskSubmission"]] = relationship(
        "EmployerTaskSubmission",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(EmployerTaskSubmission.created_at)",
    )
    activities: Mapped[list["CandidateActivity"]] = relationship(
        "CandidateActivity",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="desc(CandidateActivity.created_at)",
    )
