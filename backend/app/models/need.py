from typing import TYPE_CHECKING, Any
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employer import EmployerProfile
    from app.models.invitation import Invitation


class EmployerNeed(Base, TimestampMixin):
    __tablename__ = "employer_needs"

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
    required_skills: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    salary_min: Mapped[float] = mapped_column(Float, nullable=False)
    salary_max: Mapped[float] = mapped_column(Float, nullable=False)
    # Пометка «до вычета НДФЛ» (gross) или «на руки» (net)
    salary_tax_type: Mapped[str] = mapped_column(String(20), default="gross", nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)

    work_format: Mapped[str] = mapped_column(String(50), default="remote", nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employer: Mapped["EmployerProfile"] = relationship(
        "EmployerProfile", back_populates="needs"
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation", back_populates="need", cascade="all, delete-orphan"
    )
