"""Allow one full retake linked to its original grade assessment.

Revision ID: 004_full_roadmap_retake
Revises: 003_grade_assessments
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_full_roadmap_retake"
down_revision: Union[str, None] = "003_grade_assessments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("grade_assessments", sa.Column("retake_of_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_grade_assessments_retake_of_id", "grade_assessments", "grade_assessments",
        ["retake_of_id"], ["id"], ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_grade_assessments_retake_of_id", "grade_assessments", ["retake_of_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_grade_assessments_retake_of_id", "grade_assessments", type_="unique")
    op.drop_constraint("fk_grade_assessments_retake_of_id", "grade_assessments", type_="foreignkey")
    op.drop_column("grade_assessments", "retake_of_id")
