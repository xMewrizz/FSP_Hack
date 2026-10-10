"""Store candidate specializations independently from the primary profile."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_candidate_specialization_tracks"
down_revision: Union[str, Sequence[str], None] = (
    "007_open_assessment",
    "007_employer_candidate_workspaces",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_specialization_tracks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("candidate_profile_id", sa.UUID(), nullable=False),
        sa.Column("specialization", sa.String(length=100), nullable=False),
        sa.Column("verified_grade", sa.String(length=50), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_profile_id",
            "specialization",
            name="uq_candidate_specialization_track",
        ),
    )
    op.create_index(
        op.f("ix_candidate_specialization_tracks_candidate_profile_id"),
        "candidate_specialization_tracks",
        ["candidate_profile_id"],
    )
    op.create_index(
        op.f("ix_candidate_specialization_tracks_specialization"),
        "candidate_specialization_tracks",
        ["specialization"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_candidate_specialization_tracks_specialization"),
        table_name="candidate_specialization_tracks",
    )
    op.drop_index(
        op.f("ix_candidate_specialization_tracks_candidate_profile_id"),
        table_name="candidate_specialization_tracks",
    )
    op.drop_table("candidate_specialization_tracks")
