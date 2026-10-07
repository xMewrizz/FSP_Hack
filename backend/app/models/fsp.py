from typing import TYPE_CHECKING
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate import CandidateProfile


class FSPAchievement(Base, TimestampMixin):
    __tablename__ = "fsp_achievements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    fsp_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    tournament_name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_or_place: Mapped[str] = mapped_column(String(100), nullable=False)
    sport_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score_or_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="fsp_achievements",
    )
