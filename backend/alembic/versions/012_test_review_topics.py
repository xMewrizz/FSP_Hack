"""Store skill topics suggested after a finished test."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_test_review_topics"
down_revision: Union[str, Sequence[str], None] = "012_specialization_declared_grade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_sessions",
        sa.Column("review_topics", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "test_sessions",
        sa.Column("review_topics_status", sa.String(length=20), nullable=False, server_default="none"),
    )


def downgrade() -> None:
    op.drop_column("test_sessions", "review_topics_status")
    op.drop_column("test_sessions", "review_topics")
