import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class EmployerOrganization(Base, TimestampMixin):
    __tablename__ = "employer_organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )


class EmployerTeamInvitation(Base, TimestampMixin):
    __tablename__ = "employer_team_invitations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'accepted', 'cancelled')", name="ck_team_invitation_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employer_organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    invited_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_role: Mapped[str] = mapped_column(String(20), default="hr", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CandidateReview(Base, TimestampMixin):
    __tablename__ = "candidate_reviews"
    __table_args__ = (
        UniqueConstraint("organization_id", "candidate_profile_id"),
        CheckConstraint(
            "pipeline_status IN ('new', 'contact_search', 'contacted', 'screening', 'interview', 'offer', 'onboarding', 'mentor_work', 'hired', 'rejected')",
            name="ck_candidate_review_pipeline_status",
        ),
        CheckConstraint(
            "contact_status IN ('not_started', 'searching', 'found', 'unavailable')",
            name="ck_candidate_review_contact_status",
        ),
        CheckConstraint(
            "background_check_status IN ('not_started', 'pending', 'clear', 'review', 'blocked')",
            name="ck_candidate_review_background_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employer_organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    pipeline_status: Mapped[str] = mapped_column(String(30), default="new", nullable=False)
    contact_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    background_check_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    messages: Mapped[list["CandidateReviewMessage"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="CandidateReviewMessage.created_at"
    )


class CandidateReviewMessage(Base):
    __tablename__ = "candidate_review_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review: Mapped[CandidateReview] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship("User")


from app.models.user import User
