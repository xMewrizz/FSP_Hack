"""A candidate's saved resume text, retained for comparison with later versions."""

import uuid

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ResumeVersion(Base, TimestampMixin):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    work_lines: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
