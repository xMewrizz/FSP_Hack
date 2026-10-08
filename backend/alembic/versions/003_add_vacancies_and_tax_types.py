"""add vacancies, vacancy applications, and tax types

Revision ID: 003_vacancies_and_tax_types
Revises: 002_testing_needs_invitations
Create Date: 2026-10-08 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_vacancies_and_tax_types'
down_revision: Union[str, None] = '002_testing_needs_invitations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add salary_tax_type to employer_needs and invitations
    op.add_column('employer_needs', sa.Column('salary_tax_type', sa.String(length=20), nullable=False, server_default='gross'))
    op.add_column('invitations', sa.Column('salary_tax_type', sa.String(length=20), nullable=False, server_default='gross'))

    # 2. Add is_demo and disclaimer to fsp_achievements
    op.add_column('fsp_achievements', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('fsp_achievements', sa.Column('disclaimer', sa.String(length=255), nullable=False, server_default='Демонстрационные данные стенда. Не является официальной выпиской реестра ФСП'))

    # 3. Create vacancies table
    op.create_table(
        'vacancies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('employer_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('specialization', sa.String(length=100), nullable=False),
        sa.Column('required_grade', sa.String(length=50), nullable=False),
        sa.Column('required_skills', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('salary_min', sa.Float(), nullable=False),
        sa.Column('salary_max', sa.Float(), nullable=False),
        sa.Column('salary_tax_type', sa.String(length=20), nullable=False, server_default='gross'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='RUB'),
        sa.Column('work_format', sa.String(length=50), nullable=False, server_default='remote'),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_vacancies_employer_id'), 'vacancies', ['employer_id'], unique=False)
    op.create_index(op.f('ix_vacancies_specialization'), 'vacancies', ['specialization'], unique=False)
    op.create_index(op.f('ix_vacancies_required_grade'), 'vacancies', ['required_grade'], unique=False)

    # 4. Create vacancy_applications table
    op.create_table(
        'vacancy_applications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('vacancy_id', sa.UUID(), nullable=False),
        sa.Column('candidate_profile_id', sa.UUID(), nullable=False),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vacancy_id'], ['vacancies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vacancy_id', 'candidate_profile_id', name='uq_vacancy_candidate_application'),
    )
    op.create_index(op.f('ix_vacancy_applications_vacancy_id'), 'vacancy_applications', ['vacancy_id'], unique=False)
    op.create_index(op.f('ix_vacancy_applications_candidate_profile_id'), 'vacancy_applications', ['candidate_profile_id'], unique=False)


def downgrade() -> None:
    op.drop_table('vacancy_applications')
    op.drop_table('vacancies')
    op.drop_column('fsp_achievements', 'disclaimer')
    op.drop_column('fsp_achievements', 'is_demo')
    op.drop_column('invitations', 'salary_tax_type')
    op.drop_column('employer_needs', 'salary_tax_type')
