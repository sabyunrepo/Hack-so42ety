"""add_book_soft_delete_fields

Revision ID: 009
Revises: 008
Create Date: 2024-12-10

Add is_deleted and deleted_at fields to books table for soft delete support
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add soft delete fields to books table"""

    # Add is_deleted column (default False, indexed for quota queries)
    op.add_column('books', sa.Column('is_deleted', sa.Boolean(),
                                      server_default='false', nullable=False))

    # Add deleted_at column (nullable timestamp)
    op.add_column('books', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # Create index for quota queries: WHERE user_id = ? AND is_deleted = false
    op.create_index('idx_books_user_deleted', 'books',
                   ['user_id', 'is_deleted'], unique=False)


def downgrade() -> None:
    """Remove soft delete fields from books table"""

    # Drop index first
    op.drop_index('idx_books_user_deleted', table_name='books')

    # Drop columns
    op.drop_column('books', 'deleted_at')
    op.drop_column('books', 'is_deleted')
