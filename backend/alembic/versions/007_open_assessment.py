"""Link open answers to a frozen grade assessment.

Revision ID: 007_open_assessment
Revises: 006_mentorship_network
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_open_assessment"
down_revision: Union[str, Sequence[str], None] = "006_mentorship_network"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("open_question_submissions", sa.Column("assessment_id", sa.UUID(), nullable=True))
    op.create_index(
        "ix_open_question_submissions_assessment_id", "open_question_submissions", ["assessment_id"]
    )
    op.create_foreign_key(
        "fk_open_question_submissions_assessment_id", "open_question_submissions", "grade_assessments",
        ["assessment_id"], ["id"], ondelete="CASCADE",
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_open_submission_assessment_question "
        "ON open_question_submissions (assessment_id, question_code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_open_submission_assessment_question")
    op.drop_constraint("fk_open_question_submissions_assessment_id", "open_question_submissions", type_="foreignkey")
    op.drop_index("ix_open_question_submissions_assessment_id", table_name="open_question_submissions")
    op.drop_column("open_question_submissions", "assessment_id")
