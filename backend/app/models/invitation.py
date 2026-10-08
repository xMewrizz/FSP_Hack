from datetime import datetime
from typing import TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile
    from app.models.employer import EmployerProfile
    from app.models.need import EmployerNeed


class Invitation(Base, TimestampMixin):
    __tablename__ = "invitations"

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
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    need_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employer_needs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    offer_description: Mapped[str] = mapped_column(Text, nullable=False)
    contact_method: Mapped[str] = mapped_column(String(255), nullable=False)

    salary_min: Mapped[float] = mapped_column(Float, nullable=False)
    salary_max: Mapped[float] = mapped_column(Float, nullable=False)
    salary_tax_type: Mapped[str] = mapped_column(String(20), default="gross", nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="sent", index=True, nullable=False)
    candidate_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employer: Mapped["EmployerProfile"] = relationship(
        "EmployerProfile", back_populates="invitations"
    )
    candidate: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="invitations"
    )
    need: Mapped["EmployerNeed | None"] = relationship(
        "EmployerNeed", back_populates="invitations"
    )
