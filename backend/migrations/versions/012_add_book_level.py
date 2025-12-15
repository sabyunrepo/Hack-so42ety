"""012_add_book_level

Revision ID: 012
Revises: ea13d4af774b
Create Date: 2025-12-14

Add level field to books table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = 'ea13d4af774b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add level column to books table"""

    op.add_column(
        'books',
        sa.Column(
            'level',
            sa.Integer(),
            nullable=True,
        )
    )


def downgrade() -> None:
    """Remove level column from books table"""

    op.drop_column('books', 'level')
