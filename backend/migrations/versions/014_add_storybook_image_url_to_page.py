"""add_storybook_image_url_to_page

Revision ID: 014
Revises: 013
Create Date: 2025-12-19

Add storybook_image_url field to pages table for AI-generated images.
- image_url: Used for video URLs (frontend compatibility)
- storybook_image_url: Used for AI-generated storybook images
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add storybook_image_url column to pages table"""
    op.add_column(
        'pages',
        sa.Column(
            'storybook_image_url',
            sa.String(length=1024),
            nullable=True,
        )
    )


def downgrade() -> None:
    """Remove storybook_image_url column from pages table"""
    op.drop_column('pages', 'storybook_image_url')
