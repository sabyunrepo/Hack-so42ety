"""011_add_book_column_progress_retry

Revision ID: ea13d4af774b
Revises: 010
Create Date: 2025-12-13 18:09:19.222781

Add pipeline tracking fields to books table:
- pipeline_stage: Current pipeline stage
- task_metadata: Task execution metadata (JSONB)
- progress_percentage: Overall progress (0-100)
- error_message: Last error message if status=FAILED
- retry_count: Number of retry attempts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ea13d4af774b'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pipeline tracking fields to books table"""

    # Add pipeline_stage column
    op.add_column(
        'books',
        sa.Column(
            'pipeline_stage',
            sa.String(length=50),
            nullable=True,
            comment='Current pipeline stage: init|story|images|tts|video|finalizing|completed|failed'
        )
    )

    # Add task_metadata column (JSONB)
    op.add_column(
        'books',
        sa.Column(
            'task_metadata',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Task execution metadata: task_ids, progress, errors'
        )
    )

    # Add progress_percentage column
    op.add_column(
        'books',
        sa.Column(
            'progress_percentage',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Overall progress: 0-100'
        )
    )

    # Add error_message column
    op.add_column(
        'books',
        sa.Column(
            'error_message',
            sa.Text(),
            nullable=True,
            comment='Last error message if status=FAILED'
        )
    )

    # Add retry_count column
    op.add_column(
        'books',
        sa.Column(
            'retry_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Number of retry attempts'
        )
    )


def downgrade() -> None:
    """Remove pipeline tracking fields from books table"""

    # Drop columns in reverse order
    op.drop_column('books', 'retry_count')
    op.drop_column('books', 'error_message')
    op.drop_column('books', 'progress_percentage')
    op.drop_column('books', 'task_metadata')
    op.drop_column('books', 'pipeline_stage')
