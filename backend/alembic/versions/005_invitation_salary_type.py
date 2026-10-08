"""Record whether an invitation salary is gross or net.

Revision ID: 005_invitation_salary_type
Revises: 004_full_roadmap_retake
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_invitation_salary_type"
down_revision: Union[str, None] = "004_full_roadmap_retake"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invitations",
        sa.Column("salary_type", sa.String(length=10), server_default="gross", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("invitations", "salary_type")
