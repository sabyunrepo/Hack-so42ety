"""create_book_tables

Revision ID: 002
Revises: 001
Create Date: 2025-11-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== Books Table ====================
    op.create_table(
        'books',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('cover_image_url', sa.String(length=1024), nullable=True),
        sa.Column('genre', sa.String(length=100), nullable=True),
        sa.Column('target_age', sa.String(length=50), nullable=True),
        sa.Column('theme', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_books_id'), 'books', ['id'], unique=False)
    op.create_index(op.f('ix_books_user_id'), 'books', ['user_id'], unique=False)

    # ==================== Pages Table ====================
    op.create_table(
        'pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(length=1024), nullable=True),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_pages_id'), 'pages', ['id'], unique=False)
    op.create_index(op.f('ix_pages_book_id'), 'pages', ['book_id'], unique=False)

    # ==================== Dialogues Table ====================
    op.create_table(
        'dialogues',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('speaker', sa.String(length=100), nullable=False),
        sa.Column('text_en', sa.Text(), nullable=False),
        sa.Column('text_ko', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_dialogues_id'), 'dialogues', ['id'], unique=False)
    op.create_index(op.f('ix_dialogues_page_id'), 'dialogues', ['page_id'], unique=False)

    # ==================== Audios Table ====================
    op.create_table(
        'audios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_url', sa.String(length=1024), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=50), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('voice_id', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_audios_id'), 'audios', ['id'], unique=False)
    op.create_index(op.f('ix_audios_user_id'), 'audios', ['user_id'], unique=False)

    # ==================== Row Level Security (RLS) ====================
    
    # 1. Enable RLS on tables
    op.execute("ALTER TABLE books ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dialogues ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audios ENABLE ROW LEVEL SECURITY")

    # Force RLS for table owners (important for testing and admin access)
    op.execute("ALTER TABLE books FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pages FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dialogues FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audios FORCE ROW LEVEL SECURITY")

    # 2. Create Policies for Books
    # Users can only see their own books
    op.execute("""
        CREATE POLICY books_isolation_policy ON books
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)

    # 3. Create Policies for Pages
    # Users can only see pages of books they own
    op.execute("""
        CREATE POLICY pages_isolation_policy ON pages
        USING (
            book_id IN (
                SELECT id FROM books 
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
        WITH CHECK (
            book_id IN (
                SELECT id FROM books 
                WHERE user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    # 4. Create Policies for Dialogues
    # Users can only see dialogues of pages of books they own
    op.execute("""
        CREATE POLICY dialogues_isolation_policy ON dialogues
        USING (
            page_id IN (
                SELECT p.id FROM pages p
                JOIN books b ON p.book_id = b.id
                WHERE b.user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
        WITH CHECK (
            page_id IN (
                SELECT p.id FROM pages p
                JOIN books b ON p.book_id = b.id
                WHERE b.user_id = current_setting('app.current_user_id', true)::uuid
            )
        )
    """)

    # 5. Create Policies for Audios
    # Users can only see their own audios
    op.execute("""
        CREATE POLICY audios_isolation_policy ON audios
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)


def downgrade() -> None:
    # Drop Policies
    op.execute("DROP POLICY IF EXISTS audios_isolation_policy ON audios")
    op.execute("DROP POLICY IF EXISTS dialogues_isolation_policy ON dialogues")
    op.execute("DROP POLICY IF EXISTS pages_isolation_policy ON pages")
    op.execute("DROP POLICY IF EXISTS books_isolation_policy ON books")

    # Disable RLS
    op.execute("ALTER TABLE audios DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dialogues DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pages DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE books DISABLE ROW LEVEL SECURITY")

    # Drop Tables
    op.drop_index(op.f('ix_audios_user_id'), table_name='audios')
    op.drop_index(op.f('ix_audios_id'), table_name='audios')
    op.drop_table('audios')

    op.drop_index(op.f('ix_dialogues_page_id'), table_name='dialogues')
    op.drop_index(op.f('ix_dialogues_id'), table_name='dialogues')
    op.drop_table('dialogues')

    op.drop_index(op.f('ix_pages_book_id'), table_name='pages')
    op.drop_index(op.f('ix_pages_id'), table_name='pages')
    op.drop_table('pages')

    op.drop_index(op.f('ix_books_user_id'), table_name='books')
    op.drop_index(op.f('ix_books_id'), table_name='books')
    op.drop_table('books')
