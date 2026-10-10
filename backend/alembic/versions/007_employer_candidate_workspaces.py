"""Add shared employer teams and private candidate review workspaces.

Revision ID: 007_employer_candidate_workspaces
Revises: 006_mentorship_network
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_employer_candidate_workspaces"
down_revision: Union[str, Sequence[str], None] = "006_mentorship_network"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employer_organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_employer_organizations_owner_user_id"),
        "employer_organizations",
        ["owner_user_id"],
        unique=False,
    )
    op.add_column(
        "employer_profiles",
        sa.Column("organization_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_employer_profiles_organization_id"),
        "employer_profiles",
        ["organization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_employer_profiles_organization_id_employer_organizations",
        "employer_profiles",
        "employer_organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "employer_team_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("invited_email", sa.String(length=255), nullable=False),
        sa.Column("invited_by_user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("accepted_by_user_id", sa.UUID(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'cancelled')",
            name="ck_team_invitation_status",
        ),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["employer_organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_employer_team_invitations_invited_email"),
        "employer_team_invitations",
        ["invited_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_employer_team_invitations_organization_id"),
        "employer_team_invitations",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "candidate_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("pipeline_status", sa.String(length=30), nullable=False),
        sa.Column("contact_status", sa.String(length=30), nullable=False),
        sa.Column("background_check_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "pipeline_status IN ('new', 'contact_search', 'contacted', 'screening', 'interview', 'offer', 'hired', 'rejected')",
            name="ck_candidate_review_pipeline_status",
        ),
        sa.CheckConstraint(
            "contact_status IN ('not_started', 'searching', 'found', 'unavailable')",
            name="ck_candidate_review_contact_status",
        ),
        sa.CheckConstraint(
            "background_check_status IN ('not_started', 'pending', 'clear', 'review', 'blocked')",
            name="ck_candidate_review_background_status",
        ),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["employer_organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "candidate_profile_id"),
    )
    op.create_index(
        op.f("ix_candidate_reviews_candidate_profile_id"),
        "candidate_reviews",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_reviews_organization_id"),
        "candidate_reviews",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "candidate_review_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column("sender_user_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["candidate_reviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_review_messages_review_id"),
        "candidate_review_messages",
        ["review_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_review_messages_sender_user_id"),
        "candidate_review_messages",
        ["sender_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_candidate_review_messages_sender_user_id"), table_name="candidate_review_messages")
    op.drop_index(op.f("ix_candidate_review_messages_review_id"), table_name="candidate_review_messages")
    op.drop_table("candidate_review_messages")
    op.drop_index(op.f("ix_candidate_reviews_organization_id"), table_name="candidate_reviews")
    op.drop_index(op.f("ix_candidate_reviews_candidate_profile_id"), table_name="candidate_reviews")
    op.drop_table("candidate_reviews")
    op.drop_index(op.f("ix_employer_team_invitations_organization_id"), table_name="employer_team_invitations")
    op.drop_index(op.f("ix_employer_team_invitations_invited_email"), table_name="employer_team_invitations")
    op.drop_table("employer_team_invitations")
    op.drop_constraint(
        "fk_employer_profiles_organization_id_employer_organizations",
        "employer_profiles",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_employer_profiles_organization_id"), table_name="employer_profiles")
    op.drop_column("employer_profiles", "organization_id")
    op.drop_index(op.f("ix_employer_organizations_owner_user_id"), table_name="employer_organizations")
    op.drop_table("employer_organizations")
