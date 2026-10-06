"""add testing needs and invitations

Revision ID: 002_testing_needs_invitations
Revises: 001_auth_onboarding
Create Date: 2026-10-06 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_testing_needs_invitations'
down_revision: Union[str, None] = '001_auth_onboarding'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update candidate_profiles
    op.add_column('candidate_profiles', sa.Column('verified_grade_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('candidate_profiles', sa.Column('salary_expectation', sa.Float(), nullable=True))
    op.add_column('candidate_profiles', sa.Column('skills', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('candidate_profiles', sa.Column('visibility_public', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('candidate_profiles', sa.Column('resume_text', sa.Text(), nullable=True))

    # 2. questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('specialization', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.String(length=50), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False, server_default='single_choice'),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('correct_answers', sa.JSON(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False, server_default=''),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_questions_code'), 'questions', ['code'], unique=True)
    op.create_index(op.f('ix_questions_specialization'), 'questions', ['specialization'], unique=False)
    op.create_index(op.f('ix_questions_grade'), 'questions', ['grade'], unique=False)

    # 3. test_sessions table
    op.create_table(
        'test_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('candidate_profile_id', sa.UUID(), nullable=False),
        sa.Column('specialization', sa.String(length=100), nullable=False),
        sa.Column('target_grade', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_progress'),
        sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('max_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('skill_breakdown', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('questions_snapshot', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('answers_data', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('suggested_grade', sa.String(length=50), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_test_sessions_user_id'), 'test_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_test_sessions_candidate_profile_id'), 'test_sessions', ['candidate_profile_id'], unique=False)

    # 4. employer_needs table
    op.create_table(
        'employer_needs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('employer_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('specialization', sa.String(length=100), nullable=False),
        sa.Column('required_grade', sa.String(length=50), nullable=False),
        sa.Column('required_skills', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('salary_min', sa.Float(), nullable=False),
        sa.Column('salary_max', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='RUB'),
        sa.Column('work_format', sa.String(length=50), nullable=False, server_default='remote'),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_employer_needs_employer_id'), 'employer_needs', ['employer_id'], unique=False)
    op.create_index(op.f('ix_employer_needs_specialization'), 'employer_needs', ['specialization'], unique=False)

    # 5. invitations table
    op.create_table(
        'invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('employer_id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('need_id', sa.UUID(), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('offer_description', sa.Text(), nullable=False),
        sa.Column('contact_method', sa.String(length=255), nullable=False),
        sa.Column('salary_min', sa.Float(), nullable=False),
        sa.Column('salary_max', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='RUB'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='sent'),
        sa.Column('candidate_reply', sa.Text(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employer_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['need_id'], ['employer_needs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_invitations_employer_id'), 'invitations', ['employer_id'], unique=False)
    op.create_index(op.f('ix_invitations_candidate_id'), 'invitations', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_invitations_status'), 'invitations', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('invitations')
    op.drop_table('employer_needs')
    op.drop_table('test_sessions')
    op.drop_table('questions')
    op.drop_column('candidate_profiles', 'resume_text')
    op.drop_column('candidate_profiles', 'visibility_public')
    op.drop_column('candidate_profiles', 'skills')
    op.drop_column('candidate_profiles', 'salary_expectation')
    op.drop_column('candidate_profiles', 'verified_grade_updated_at')
