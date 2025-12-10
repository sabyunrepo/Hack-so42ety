"""initial_schema

Revision ID: 001
Revises: 
Create Date: 2025-12-10

Complete initial database schema with all tables and shared books data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Complete database schema creation including:
    - Users table
    - Books, Pages, Dialogues tables with multilanguage support
    - Dialogue Translations and Audios tables
    - Audios and Voices tables
    - Row Level Security (RLS) policies
    - Shared books data
    """
    
    # ==================== Users Table ====================
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('oauth_provider', sa.String(50), nullable=True),
        sa.Column('oauth_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ==================== Books Table ====================
    op.create_table(
        'books',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('cover_image', sa.String(1024), nullable=True),
        sa.Column('genre', sa.String(100), nullable=True),
        sa.Column('target_age', sa.String(50), nullable=True),
        sa.Column('theme', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='private'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_books_id', 'books', ['id'])
    op.create_index('ix_books_user_id', 'books', ['user_id'])
    op.create_index('ix_books_is_public', 'books', ['is_public'])
    op.create_index('ix_books_visibility', 'books', ['visibility'])

    # ==================== Pages Table ====================
    op.create_table(
        'pages',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(1024), nullable=True),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_pages_id', 'pages', ['id'])
    op.create_index('ix_pages_book_id', 'pages', ['book_id'])

    # ==================== Dialogues Table ====================
    op.create_table(
        'dialogues',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('page_id', UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('speaker', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_dialogues_id', 'dialogues', ['id'])
    op.create_index('ix_dialogues_page_id', 'dialogues', ['page_id'])

    # ==================== Dialogue Translations Table ====================
    op.create_table(
        'dialogue_translations',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('dialogue_id', UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(10), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dialogue_id'], ['dialogues.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_dialogue_translations_id', 'dialogue_translations', ['id'])
    op.create_index('idx_dialogue_language', 'dialogue_translations', ['dialogue_id', 'language_code'], unique=True)
    op.create_index('idx_language_primary', 'dialogue_translations', ['language_code', 'is_primary'])

    # ==================== Dialogue Audios Table ====================
    op.create_table(
        'dialogue_audios',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('dialogue_id', UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(10), nullable=False),
        sa.Column('voice_id', sa.String(100), nullable=False),
        sa.Column('audio_url', sa.String(1024), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dialogue_id'], ['dialogues.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_dialogue_audios_id', 'dialogue_audios', ['id'])
    op.create_index('idx_dialogue_language_voice', 'dialogue_audios', ['dialogue_id', 'language_code', 'voice_id'], unique=True)
    op.create_index('idx_audio_language', 'dialogue_audios', ['language_code'])

    # ==================== Audios Table ====================
    op.create_table(
        'audios',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('file_url', sa.String(1024), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(50), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('voice_id', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('meta_data', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_audios_id', 'audios', ['id'])
    op.create_index('ix_audios_user_id', 'audios', ['user_id'])

    # ==================== Voice Enum Types ====================
    # Create enum types safely using raw SQL with conditional checks
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'voicevisibility') THEN
                CREATE TYPE voicevisibility AS ENUM ('private', 'public', 'default');
            END IF;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'voicestatus') THEN
                CREATE TYPE voicestatus AS ENUM ('processing', 'completed', 'failed');
            END IF;
        END $$;
    """)

    # ==================== Voices Table ====================
    # Use raw SQL to create voices table to avoid enum creation issues
    op.execute("""
        CREATE TABLE voices (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            elevenlabs_voice_id VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            language VARCHAR(10) NOT NULL DEFAULT 'en',
            gender VARCHAR(20) NOT NULL DEFAULT 'unknown',
            preview_url VARCHAR(1024),
            category VARCHAR(50) NOT NULL DEFAULT 'cloned',
            visibility voicevisibility NOT NULL DEFAULT 'private',
            status voicestatus NOT NULL DEFAULT 'processing',
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            meta_data JSON
        );
    """)
    # Create indexes for voices table
    op.execute("CREATE INDEX ix_voices_id ON voices(id);")
    op.execute("CREATE INDEX idx_voice_user_id ON voices(user_id);")
    op.execute("CREATE INDEX idx_voice_status ON voices(status);")
    op.execute("CREATE INDEX idx_voice_visibility ON voices(visibility);")
    op.execute("CREATE INDEX idx_voice_user_status ON voices(user_id, status);")
    op.execute("CREATE INDEX idx_voice_visibility_status ON voices(visibility, status);")
    op.execute("CREATE INDEX idx_voice_elevenlabs_id ON voices(elevenlabs_voice_id);")
    op.execute("CREATE INDEX idx_voice_created_at ON voices(created_at);")

    # ==================== Row Level Security (RLS) ====================
    
    # Enable RLS on tables
    op.execute("ALTER TABLE books ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dialogues ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audios ENABLE ROW LEVEL SECURITY")

    # Force RLS for table owners
    op.execute("ALTER TABLE books FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pages FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dialogues FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audios FORCE ROW LEVEL SECURITY")

    # Create Policies
    op.execute("""
        CREATE POLICY books_isolation_policy ON books
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)

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

    op.execute("""
        CREATE POLICY audios_isolation_policy ON audios
        USING (user_id = current_setting('app.current_user_id', true)::uuid)
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)

    # ==================== Initial Data: System User ====================
    system_user_id = '00000000-0000-0000-0000-000000000001'
    
    op.execute(f"""
        INSERT INTO users (id, email, is_active, created_at, updated_at)
        VALUES (
            '{system_user_id}'::uuid,
            'system@moriai.ai',
            true,
            NOW(),
            NOW()
        );
    """)

    # ==================== Initial Data: Shared Book 1 ====================
    book_1_id = '1c8e135a-8e4a-46fb-ac24-13baaacfd586'
    
    op.execute(f"""
        INSERT INTO books (id, user_id, title, cover_image, status, is_default, is_public, visibility, created_at, updated_at)
        VALUES (
            '{book_1_id}'::uuid,
            '{system_user_id}'::uuid,
            'My Playground Day',
            '/api/v1/files/shared/books/{book_1_id}/videos/page_1.mp4',
            'completed',
            true,
            true,
            'public',
            '2025-11-01T14:19:40.486916'::timestamp,
            NOW()
        );
    """)
    
    # Book 1 Pages
    pages_book_1 = [
        ('f4fe37c1-876b-4628-a3a4-f92112c96b26', 1, f'/api/v1/files/shared/books/{book_1_id}/videos/page_1.mp4'),
        ('d2fc4c22-762f-44f9-904a-9d887718b5b0', 2, f'/api/v1/files/shared/books/{book_1_id}/videos/page_2.mp4'),
        ('e4e92c8b-2654-4da5-8116-60325b599785', 3, f'/api/v1/files/shared/books/{book_1_id}/videos/page_3.mp4'),
        ('418dcd35-92b8-4399-a109-f3e37d536f2c', 4, f'/api/v1/files/shared/books/{book_1_id}/videos/page_4.mp4'),
        ('1b486846-cfe8-4b17-aeeb-23b01fd82c07', 5, f'/api/v1/files/shared/books/{book_1_id}/videos/page_5.mp4'),
    ]
    
    for page_id, seq, image_url in pages_book_1:
        op.execute(f"""
            INSERT INTO pages (id, book_id, sequence, image_url, created_at, updated_at)
            VALUES (
                '{page_id}'::uuid,
                '{book_1_id}'::uuid,
                {seq},
                '{image_url}',
                NOW(),
                NOW()
            );
        """)

    # Book 1 Dialogues
    dialogues_book_1 = [
        ('0fd5f91b-324b-4490-b99b-1cb1c60e07b9', 'f4fe37c1-876b-4628-a3a4-f92112c96b26', 1, 'Narrator', 'I am at the playground. With my friends.'),
        ('bff6d8f3-21d3-4ea5-bfb5-8e2da80bcdb8', 'd2fc4c22-762f-44f9-904a-9d887718b5b0', 1, 'Narrator', 'We play hanging. I hang strong! Wow, I am so high!'),
        ('89eca997-b44f-4c7f-a8f4-41d422a81314', 'e4e92c8b-2654-4da5-8116-60325b599785', 1, 'Narrator', 'We play with bubbles. Pop, pop, pop! So many bubbles!'),
        ('3d18406e-ea09-4c9c-9b93-cdd4e9c2c8e2', '418dcd35-92b8-4399-a109-f3e37d536f2c', 1, 'Narrator', 'Now we jump on the trampoline. Jump, jump, jump!'),
        ('7ac09c6e-3fa3-4f1c-be13-0ad28a30f4fe', '1b486846-cfe8-4b17-aeeb-23b01fd82c07', 1, 'Narrator', 'Time to go home. What a fun day!'),
    ]
    
    for dialogue_id, page_id, seq, speaker, text_en in dialogues_book_1:
        op.execute(f"""
            INSERT INTO dialogues (id, page_id, sequence, speaker, created_at, updated_at)
            VALUES (
                '{dialogue_id}'::uuid,
                '{page_id}'::uuid,
                {seq},
                '{speaker}',
                NOW(),
                NOW()
            );
        """)
        
        op.execute(f"""
            INSERT INTO dialogue_translations (id, dialogue_id, language_code, text, is_primary, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                '{dialogue_id}'::uuid,
                'en',
                $${text_en}$$,
                true,
                NOW(),
                NOW()
            );
        """)
        
        op.execute(f"""
            INSERT INTO dialogue_audios (id, dialogue_id, language_code, voice_id, audio_url, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                '{dialogue_id}'::uuid,
                'en',
                'uzyfnLLlKo55AbgBU5uH',
                '/api/v1/files/shared/books/{book_1_id}/audios/{dialogue_id}.mp3',
                NOW(),
                NOW()
            );
        """)

    # ==================== Initial Data: Shared Book 2 ====================
    book_2_id = '32e543c7-a845-4cfb-a93d-a0153dc9e063'
    
    op.execute(f"""
        INSERT INTO books (id, user_id, title, cover_image, status, is_default, is_public, visibility, created_at, updated_at)
        VALUES (
            '{book_2_id}'::uuid,
            '{system_user_id}'::uuid,
            'My Mountain Adventure',
            '/api/v1/files/shared/books/{book_2_id}/videos/page_1.mp4',
            'completed',
            true,
            true,
            'public',
            '2025-11-01T14:19:40.486916'::timestamp,
            NOW()
        );
    """)
    
    # Book 2 Pages
    pages_book_2 = [
        ('3baf370f-8f4c-4bef-b091-6c3f2bc34cd4', 1, f'/api/v1/files/shared/books/{book_2_id}/videos/page_1.mp4'),
        ('7e409966-7aa9-4d8c-83a3-d344cba3a120', 2, f'/api/v1/files/shared/books/{book_2_id}/videos/page_2.mp4'),
        ('ebe3f128-2e74-47e4-ab9a-80c2fffabe5c', 3, f'/api/v1/files/shared/books/{book_2_id}/videos/page_3.mp4'),
        ('c0129b75-faea-4207-92db-606339c1a89f', 4, f'/api/v1/files/shared/books/{book_2_id}/videos/page_4.mp4'),
    ]
    
    for page_id, seq, image_url in pages_book_2:
        op.execute(f"""
            INSERT INTO pages (id, book_id, sequence, image_url, created_at, updated_at)
            VALUES (
                '{page_id}'::uuid,
                '{book_2_id}'::uuid,
                {seq},
                '{image_url}',
                NOW(),
                NOW()
            );
        """)


def downgrade() -> None:
    """Drop all tables and types"""
    
    # Drop RLS Policies
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
    op.drop_table('voices')
    op.drop_table('audios')
    op.drop_table('dialogue_audios')
    op.drop_table('dialogue_translations')
    op.drop_table('dialogues')
    op.drop_table('pages')
    op.drop_table('books')
    op.drop_table('users')
    
    # Drop Types
    op.execute('DROP TYPE IF EXISTS voicestatus')
    op.execute('DROP TYPE IF EXISTS voicevisibility')
