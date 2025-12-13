"""add_dialogue_audio_status

Revision ID: 010
Revises: 009
Create Date: 2025-12-13

Add status column to dialogue_audios table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column as nullable first to allow population
    op.add_column('dialogue_audios', sa.Column('status', sa.String(length=20), nullable=True))
    
    # Update existing records to 'COMPLETED' (legacy data assumption)
    op.execute("UPDATE dialogue_audios SET status = 'COMPLETED'")
    
    # Alter column to be non-nullable and set default for new rows
    # We set server_default to 'PENDING' so that if insert doesn't specify it, it defaults to PENDING
    op.alter_column('dialogue_audios', 'status',
               existing_type=sa.String(length=20),
               nullable=False,
               server_default='PENDING')


def downgrade() -> None:
    op.drop_column('dialogue_audios', 'status')
