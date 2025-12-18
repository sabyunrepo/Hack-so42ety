"""rename_is_public_to_is_shared

Revision ID: 013
Revises: 012
Create Date: 2025-12-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column is_public to is_shared
    op.alter_column('books', 'is_public', new_column_name='is_shared')
    
    # Update index name if necessary (optional but good practice)
    # Check if index exists with old name and rename it
    # Postgres automatically renames indexes on column rename usually, 
    # but explicit index rename is safer if we defined it with a specific name.
    # Original definition: op.create_index('ix_books_is_public', 'books', ['is_public'])
    
    # Try to rename index if it exists, assume standard naming convention
    try:
        op.execute('ALTER INDEX IF EXISTS ix_books_is_public RENAME TO ix_books_is_shared')
    except Exception:
        pass # Ignore if index doesn't exist or DB doesn't support this syntax simply


def downgrade() -> None:
    # Rename column is_shared back to is_public
    op.alter_column('books', 'is_shared', new_column_name='is_public')
    
    # Rename index back
    try:
        op.execute('ALTER INDEX IF EXISTS ix_books_is_shared RENAME TO ix_books_is_public')
    except Exception:
        pass
