"""Store an independent declared grade for each candidate specialization."""

from alembic import op
import sqlalchemy as sa


revision = "012_specialization_declared_grade"
down_revision = "011_candidate_hobbies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_specialization_tracks",
        sa.Column("declared_grade", sa.String(length=50), nullable=False, server_default="junior"),
    )
    op.execute(sa.text("""
        UPDATE candidate_specialization_tracks AS track
        SET declared_grade = COALESCE(profile.declared_grade, 'junior')
        FROM candidate_profiles AS profile
        WHERE profile.id = track.candidate_profile_id
    """))
    op.alter_column("candidate_specialization_tracks", "declared_grade", server_default=None)


def downgrade() -> None:
    op.drop_column("candidate_specialization_tracks", "declared_grade")
