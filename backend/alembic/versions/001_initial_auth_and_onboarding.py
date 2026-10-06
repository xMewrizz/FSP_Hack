"""initial auth and onboarding

Revision ID: 001_auth_onboarding
Revises: 
Create Date: 2026-10-06 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_auth_onboarding'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. email_verifications table
    op.create_table(
        'email_verifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_verifications_user_id'), 'email_verifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_email_verifications_code'), 'email_verifications', ['code'], unique=False)

    # 3. refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)

    # 4. candidate_profiles table
    op.create_table(
        'candidate_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('last_name', sa.String(length=100), nullable=False, server_default=''),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('telegram', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('github_url', sa.String(length=255), nullable=True),
        sa.Column('resume_url', sa.String(length=512), nullable=True),
        sa.Column('specialization', sa.String(length=100), nullable=True),
        sa.Column('declared_grade', sa.String(length=50), nullable=True),
        sa.Column('verified_grade', sa.String(length=50), nullable=True),
        sa.Column('work_format', sa.String(length=50), nullable=True, server_default='remote'),
        sa.Column('fsp_id', sa.String(length=100), nullable=True),
        sa.Column('fsp_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('agreed_152_fz', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('agreed_152_fz_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agreed_osint', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('agreed_osint_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_candidate_profiles_specialization'), 'candidate_profiles', ['specialization'], unique=False)
    op.create_index(op.f('ix_candidate_profiles_declared_grade'), 'candidate_profiles', ['declared_grade'], unique=False)
    op.create_index(op.f('ix_candidate_profiles_fsp_id'), 'candidate_profiles', ['fsp_id'], unique=False)

    # 5. employer_profiles table
    op.create_table(
        'employer_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('contact_person', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # 6. fsp_achievements table
    op.create_table(
        'fsp_achievements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('candidate_profile_id', sa.UUID(), nullable=False),
        sa.Column('fsp_id', sa.String(length=100), nullable=False),
        sa.Column('tournament_name', sa.String(length=255), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('rank_or_place', sa.String(length=100), nullable=False),
        sa.Column('sport_category', sa.String(length=100), nullable=True),
        sa.Column('score_or_rating', sa.Float(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_profile_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fsp_achievements_fsp_id'), 'fsp_achievements', ['fsp_id'], unique=False)
    op.create_index(op.f('ix_fsp_achievements_candidate_profile_id'), 'fsp_achievements', ['candidate_profile_id'], unique=False)


def downgrade() -> None:
    op.drop_table('fsp_achievements')
    op.drop_table('employer_profiles')
    op.drop_table('candidate_profiles')
    op.drop_table('refresh_tokens')
    op.drop_table('email_verifications')
    op.drop_table('users')
