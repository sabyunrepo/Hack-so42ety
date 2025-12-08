"""create voice table

Revision ID: 005
Revises: 004
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== Voice Enum Types ====================
    # VoiceVisibility Enum
    op.execute("CREATE TYPE voicevisibility AS ENUM ('private', 'public', 'default')")
    
    # VoiceStatus Enum
    op.execute("CREATE TYPE voicestatus AS ENUM ('processing', 'completed', 'failed')")
    
    # ==================== Voices Table ====================
    op.create_table(
        'voices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('elevenlabs_voice_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('gender', sa.String(length=20), nullable=False, server_default='unknown'),
        sa.Column('preview_url', sa.String(length=1024), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='cloned'),
        sa.Column('visibility', sa.Enum('private', 'public', 'default', name='voicevisibility'), nullable=False, server_default='private'),
        sa.Column('status', sa.Enum('processing', 'completed', 'failed', name='voicestatus'), nullable=False, server_default='processing'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', postgresql.JSON, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # ==================== Indexes ====================
    op.create_index(op.f('ix_voices_id'), 'voices', ['id'], unique=False)
    op.create_index('idx_voice_user_id', 'voices', ['user_id'], unique=False)
    op.create_index('idx_voice_status', 'voices', ['status'], unique=False)
    op.create_index('idx_voice_visibility', 'voices', ['visibility'], unique=False)
    op.create_index('idx_voice_user_status', 'voices', ['user_id', 'status'], unique=False)
    op.create_index('idx_voice_visibility_status', 'voices', ['visibility', 'status'], unique=False)
    op.create_index('idx_voice_elevenlabs_id', 'voices', ['elevenlabs_voice_id'], unique=True)
    op.create_index('idx_voice_created_at', 'voices', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_voice_created_at', table_name='voices')
    op.drop_index('idx_voice_elevenlabs_id', table_name='voices')
    op.drop_index('idx_voice_visibility_status', table_name='voices')
    op.drop_index('idx_voice_user_status', table_name='voices')
    op.drop_index('idx_voice_visibility', table_name='voices')
    op.drop_index('idx_voice_status', table_name='voices')
    op.drop_index('idx_voice_user_id', table_name='voices')
    op.drop_index(op.f('ix_voices_id'), table_name='voices')
    
    # Drop table
    op.drop_table('voices')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS voicestatus')
    op.execute('DROP TYPE IF EXISTS voicevisibility')

