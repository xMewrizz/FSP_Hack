from typing import TYPE_CHECKING
import uuid
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employer_task import EmployerTask
    from app.models.invitation import Invitation
    from app.models.need import EmployerNeed
    from app.models.user import User
    from app.models.vacancy import Vacancy


class EmployerProfile(Base, TimestampMixin):
    __tablename__ = "employer_profiles"

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

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="employer_profile")
    needs: Mapped[list["EmployerNeed"]] = relationship(
        "EmployerNeed",
        back_populates="employer",
        cascade="all, delete-orphan",
        order_by="desc(EmployerNeed.created_at)",
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation",
        back_populates="employer",
        cascade="all, delete-orphan",
        order_by="desc(Invitation.created_at)",
    )
    vacancies: Mapped[list["Vacancy"]] = relationship(
        "Vacancy",
        back_populates="employer",
        cascade="all, delete-orphan",
        order_by="desc(Vacancy.created_at)",
    )
    tasks: Mapped[list["EmployerTask"]] = relationship(
        "EmployerTask",
        back_populates="employer",
        cascade="all, delete-orphan",
        order_by="desc(EmployerTask.created_at)",
    )
