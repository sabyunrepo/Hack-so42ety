"""add multilanguage support tables

Revision ID: 004
Revises: 003
Create Date: 2025-12-01 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== DialogueTranslation Table ====================
    op.create_table(
        'dialogue_translations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dialogue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dialogue_id'], ['dialogues.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_dialogue_translations_id'), 'dialogue_translations', ['id'], unique=False)
    # Composite unique index: dialogue + language combination
    op.create_index('idx_dialogue_language', 'dialogue_translations', ['dialogue_id', 'language_code'], unique=True)
    # Performance index: language + primary flag
    op.create_index('idx_language_primary', 'dialogue_translations', ['language_code', 'is_primary'], unique=False)

    # ==================== DialogueAudio Table ====================
    op.create_table(
        'dialogue_audios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dialogue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('language_code', sa.String(length=10), nullable=False),
        sa.Column('voice_id', sa.String(length=100), nullable=False),
        sa.Column('audio_url', sa.String(length=1024), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dialogue_id'], ['dialogues.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_dialogue_audios_id'), 'dialogue_audios', ['id'], unique=False)
    # Composite unique index: dialogue + language + voice combination
    op.create_index('idx_dialogue_language_voice', 'dialogue_audios', ['dialogue_id', 'language_code', 'voice_id'], unique=True)
    # Performance index: language search
    op.create_index('idx_audio_language', 'dialogue_audios', ['language_code'], unique=False)

    # ==================== Modify Dialogues Table ====================
    # Make old columns nullable (DEPRECATED, will be removed after data migration)
    op.alter_column('dialogues', 'text_en',
                    existing_type=sa.Text(),
                    nullable=True)


def downgrade() -> None:
    # Restore text_en to non-nullable
    op.alter_column('dialogues', 'text_en',
                    existing_type=sa.Text(),
                    nullable=False)

    # Drop DialogueAudio table
    op.drop_index('idx_audio_language', table_name='dialogue_audios')
    op.drop_index('idx_dialogue_language_voice', table_name='dialogue_audios')
    op.drop_index(op.f('ix_dialogue_audios_id'), table_name='dialogue_audios')
    op.drop_table('dialogue_audios')

    # Drop DialogueTranslation table
    op.drop_index('idx_language_primary', table_name='dialogue_translations')
    op.drop_index('idx_dialogue_language', table_name='dialogue_translations')
    op.drop_index(op.f('ix_dialogue_translations_id'), table_name='dialogue_translations')
    op.drop_table('dialogue_translations')
