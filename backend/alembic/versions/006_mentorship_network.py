"""Add opt-in mentorship networking conversations.

Revision ID: 006_mentorship_network
Revises: 005_invitation_conversations
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_mentorship_network"
down_revision: Union[str, Sequence[str], None] = "005_invitation_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column("mentor_available", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "network_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("requester_user_id", sa.UUID(), nullable=False),
        sa.Column("mentor_user_id", sa.UUID(), nullable=False),
        sa.Column("skill_focus", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_network_conversations_requester_user_id"),
        "network_conversations",
        ["requester_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_network_conversations_mentor_user_id"),
        "network_conversations",
        ["mentor_user_id"],
        unique=False,
    )
    op.create_table(
        "network_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("sender_user_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["network_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_network_messages_conversation_id"),
        "network_messages",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_network_messages_sender_user_id"),
        "network_messages",
        ["sender_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_network_messages_sender_user_id"), table_name="network_messages")
    op.drop_index(op.f("ix_network_messages_conversation_id"), table_name="network_messages")
    op.drop_table("network_messages")
    op.drop_index(op.f("ix_network_conversations_mentor_user_id"), table_name="network_conversations")
    op.drop_index(op.f("ix_network_conversations_requester_user_id"), table_name="network_conversations")
    op.drop_table("network_conversations")
    op.drop_column("candidate_profiles", "mentor_available")
