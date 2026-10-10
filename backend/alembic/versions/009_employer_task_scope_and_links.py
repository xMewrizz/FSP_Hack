"""Add specialization scope and evaluation metadata to employer tasks."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_employer_task_scope_and_links"
down_revision: Union[str, Sequence[str], None] = "008_candidate_specialization_tracks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employer_tasks", sa.Column("specialization", sa.String(100), nullable=True))
    op.add_column("employer_tasks", sa.Column("min_grade", sa.String(20), nullable=True))
    op.add_column("employer_tasks", sa.Column("max_grade", sa.String(20), nullable=True))
    op.add_column(
        "employer_tasks",
        sa.Column("evaluation_criteria", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "employer_tasks",
        sa.Column("resource_links", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "employer_tasks",
        sa.Column("is_platform_task", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "employer_task_submissions",
        sa.Column("answer_links", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "employer_task_submissions",
        sa.Column("contact_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "task_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("submission_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["employer_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["employer_task_submissions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_attachments_owner_user_id", "task_attachments", ["owner_user_id"])
    op.create_index("ix_task_attachments_task_id", "task_attachments", ["task_id"])
    op.create_index("ix_task_attachments_submission_id", "task_attachments", ["submission_id"])
    op.create_index(
        op.f("ix_employer_tasks_specialization"),
        "employer_tasks",
        ["specialization"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_employer_tasks_specialization"), table_name="employer_tasks")
    op.drop_index("ix_task_attachments_submission_id", table_name="task_attachments")
    op.drop_index("ix_task_attachments_task_id", table_name="task_attachments")
    op.drop_index("ix_task_attachments_owner_user_id", table_name="task_attachments")
    op.drop_table("task_attachments")
    op.drop_column("employer_task_submissions", "contact_consent")
    op.drop_column("employer_task_submissions", "answer_links")
    op.drop_column("employer_tasks", "is_platform_task")
    op.drop_column("employer_tasks", "resource_links")
    op.drop_column("employer_tasks", "evaluation_criteria")
    op.drop_column("employer_tasks", "max_grade")
    op.drop_column("employer_tasks", "min_grade")
    op.drop_column("employer_tasks", "specialization")
