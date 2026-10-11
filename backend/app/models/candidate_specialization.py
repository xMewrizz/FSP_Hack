import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CandidateSpecializationTrack(Base, TimestampMixin):
    __tablename__ = "candidate_specialization_tracks"
    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id",
            "specialization",
            name="uq_candidate_specialization_track",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    specialization: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    declared_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    verified_grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
