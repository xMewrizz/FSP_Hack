"""Add candidate profile fields missing from the original schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011_candidate_hobbies"
down_revision: Union[str, Sequence[str], None] = "010_resume_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("hobbies", sa.Text(), nullable=True))
    op.add_column(
        "candidate_profiles",
        sa.Column("education_level", sa.String(40), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("university_course", sa.Integer(), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("birth_year", sa.Integer(), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("agreed_fsp_id_link", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("agreed_fsp_id_link_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "agreed_test_confidentiality",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("agreed_test_confidentiality_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("mentor_available", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "employer_profiles",
        sa.Column("team_role", sa.String(20), nullable=False, server_default="hr"),
    )


def downgrade() -> None:
    op.drop_column("employer_profiles", "team_role")
    op.drop_column("candidate_profiles", "mentor_available")
    op.drop_column("candidate_profiles", "agreed_test_confidentiality_at")
    op.drop_column("candidate_profiles", "agreed_test_confidentiality")
    op.drop_column("candidate_profiles", "agreed_fsp_id_link_at")
    op.drop_column("candidate_profiles", "agreed_fsp_id_link")
    op.drop_column("candidate_profiles", "birth_year")
    op.drop_column("candidate_profiles", "university_course")
    op.drop_column("candidate_profiles", "education_level")
    op.drop_column("candidate_profiles", "hobbies")
