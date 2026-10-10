"""Keep candidate-confirmed resume versions for change review."""

from alembic import op
import sqlalchemy as sa

revision = "010_resume_versions"
down_revision = "009_employer_task_scope_and_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("candidate_profile_id", sa.UUID(), sa.ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("work_lines", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_versions_candidate_profile_id", "resume_versions", ["candidate_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_versions_candidate_profile_id", table_name="resume_versions")
    op.drop_table("resume_versions")
