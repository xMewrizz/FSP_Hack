"""add salary tax type to needs and candidates

Revision ID: 003_salary_tax_type
Revises: 002_testing_needs_invitations
Create Date: 2026-10-08 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_salary_tax_type'
down_revision: Union[str, None] = '002_testing_needs_invitations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'employer_needs',
        sa.Column('salary_tax_type', sa.String(length=20), nullable=False, server_default='gross'),
    )
    op.add_column(
        'candidate_profiles',
        sa.Column('salary_tax_type', sa.String(length=20), nullable=False, server_default='gross'),
    )


def downgrade() -> None:
    op.drop_column('candidate_profiles', 'salary_tax_type')
    op.drop_column('employer_needs', 'salary_tax_type')
