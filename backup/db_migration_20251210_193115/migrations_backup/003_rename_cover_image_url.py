"""rename_cover_image_url_to_cover_image

Revision ID: 003
Revises: 002
Create Date: 2025-11-30 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Rename cover_image_url column to cover_image in books table
    """
    # Rename the column
    op.alter_column(
        'books',
        'cover_image_url',
        new_column_name='cover_image',
        existing_type=sa.String(length=1024),
        existing_nullable=True
    )


def downgrade() -> None:
    """
    Rename cover_image column back to cover_image_url in books table
    """
    # Rename the column back
    op.alter_column(
        'books',
        'cover_image',
        new_column_name='cover_image_url',
        existing_type=sa.String(length=1024),
        existing_nullable=True
    )
