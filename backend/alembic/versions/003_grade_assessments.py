"""Group separate skill tests into grade assessments.

Revision ID: 003_grade_assessments
Revises: 002_testing_needs_invitations
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_grade_assessments"
down_revision: Union[str, None] = "002_testing_needs_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("verified_specialization", sa.String(100), nullable=True))
    op.add_column("candidate_profiles", sa.Column("programming_language", sa.String(50), nullable=True))
    op.execute("UPDATE candidate_profiles SET verified_specialization = specialization WHERE verified_grade IS NOT NULL")
    op.execute("UPDATE candidate_profiles SET programming_language = 'Python' WHERE specialization = 'Backend'")
    op.create_table(
        "grade_assessments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("specialization", sa.String(100), nullable=False),
        sa.Column("programming_language", sa.String(50), nullable=True),
        sa.Column("target_grade", sa.String(50), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("question_codes", sa.JSON(), nullable=False),
        sa.Column("question_snapshots", sa.JSON(), nullable=False),
        sa.Column("retake_question_snapshots", sa.JSON(), nullable=False),
        sa.Column("scoring_policy", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="in_progress"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("suggested_grade", sa.String(50), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_grade_assessments_user_id", "grade_assessments", ["user_id"])
    op.create_index("ix_grade_assessments_candidate_profile_id", "grade_assessments", ["candidate_profile_id"])
    op.add_column("test_sessions", sa.Column("assessment_id", sa.UUID(), nullable=True))
    op.add_column("test_sessions", sa.Column("skill_code", sa.String(50), nullable=True))
    op.create_foreign_key("fk_test_sessions_assessment_id", "test_sessions", "grade_assessments", ["assessment_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_test_sessions_assessment_id", "test_sessions", ["assessment_id"])


def downgrade() -> None:
    op.drop_index("ix_test_sessions_assessment_id", table_name="test_sessions")
    op.drop_constraint("fk_test_sessions_assessment_id", "test_sessions", type_="foreignkey")
    op.drop_column("test_sessions", "skill_code")
    op.drop_column("test_sessions", "assessment_id")
    op.drop_index("ix_grade_assessments_candidate_profile_id", table_name="grade_assessments")
    op.drop_index("ix_grade_assessments_user_id", table_name="grade_assessments")
    op.drop_table("grade_assessments")
    op.drop_column("candidate_profiles", "verified_specialization")
    op.drop_column("candidate_profiles", "programming_language")
