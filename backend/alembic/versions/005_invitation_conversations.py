"""Add conversation messages for accepted invitations.

Revision ID: 005_invitation_conversations
Revises: 003_salary_tax_type, 004_full_roadmap_retake
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_invitation_conversations"
down_revision: Union[str, Sequence[str], None] = (
    "003_salary_tax_type",
    "004_full_roadmap_retake",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invitation_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invitation_id", sa.UUID(), nullable=False),
        sa.Column("sender_user_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["invitation_id"], ["invitations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invitation_messages_invitation_id"),
        "invitation_messages",
        ["invitation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invitation_messages_sender_user_id"),
        "invitation_messages",
        ["sender_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_invitation_messages_sender_user_id"), table_name="invitation_messages")
    op.drop_index(op.f("ix_invitation_messages_invitation_id"), table_name="invitation_messages")
    op.drop_table("invitation_messages")
