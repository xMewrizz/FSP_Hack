from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile
    from app.models.employer import EmployerProfile
    from app.models.employer_task import EmployerTask


class Vacancy(Base, TimestampMixin):
    __tablename__ = "vacancies"

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

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    required_grade: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    salary_min: Mapped[float] = mapped_column(Float, nullable=False)
    salary_max: Mapped[float] = mapped_column(Float, nullable=False)
    # Пометка «до вычета НДФЛ» (gross) или «на руки» (net)
    salary_tax_type: Mapped[str] = mapped_column(String(20), default="gross", nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)

    work_format: Mapped[str] = mapped_column(String(50), default="remote", nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employer: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="vacancies")
    applications: Mapped[list["VacancyApplication"]] = relationship(
        "VacancyApplication",
        back_populates="vacancy",
        cascade="all, delete-orphan",
        order_by="desc(VacancyApplication.created_at)",
    )
    tasks: Mapped[list["EmployerTask"]] = relationship(
        "EmployerTask",
        back_populates="vacancy",
    )


class VacancyApplication(Base, TimestampMixin):
    __tablename__ = "vacancy_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vacancies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending, reviewed, accepted, rejected
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", back_populates="applications")
    candidate: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="applications")
