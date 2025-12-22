"""add_video_prompt_to_page

Revision ID: 015
Revises: 014
Create Date: 2025-12-22

Add video_prompt field to pages table for video generation prompt tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add video_prompt column to pages table"""
    op.add_column(
        'pages',
        sa.Column(
            'video_prompt',
            sa.Text(),
            nullable=True,
        )
    )


def downgrade() -> None:
    """Remove video_prompt column from pages table"""
    op.drop_column('pages', 'video_prompt')
