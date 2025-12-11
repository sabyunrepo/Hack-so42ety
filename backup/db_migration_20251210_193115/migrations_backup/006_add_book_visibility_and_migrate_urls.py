"""add book visibility fields and migrate file urls

Revision ID: 006
Revises: 005
Create Date: 2024-12-08 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== Book 모델에 공개/비공개 필드 추가 ====================
    op.add_column('books', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('books', sa.Column('visibility', sa.String(length=20), nullable=False, server_default='private'))
    op.create_index('ix_books_is_public', 'books', ['is_public'])
    op.create_index('ix_books_visibility', 'books', ['visibility'])
    
    # ==================== 기존 URL 마이그레이션 (/static/ → /api/v1/files/) ====================
    # Pages 테이블의 image_url 업데이트
    op.execute("""
        UPDATE pages
        SET image_url = REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(image_url, 'http://localhost:8000/static/', '/api/v1/files/'),
                    'http://localhost/static/', '/api/v1/files/'
                ),
                'https://localhost:8000/static/', '/api/v1/files/'
            ),
            'https://localhost/static/', '/api/v1/files/'
        )
        WHERE image_url LIKE '%/static/%'
    """)
    
    # DialogueAudios 테이블의 audio_url 업데이트
    op.execute("""
        UPDATE dialogue_audios
        SET audio_url = REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(audio_url, 'http://localhost:8000/static/', '/api/v1/files/'),
                    'http://localhost/static/', '/api/v1/files/'
                ),
                'https://localhost:8000/static/', '/api/v1/files/'
            ),
            'https://localhost/static/', '/api/v1/files/'
        )
        WHERE audio_url LIKE '%/static/%'
    """)
    
    # Audios 테이블의 file_url 업데이트
    op.execute("""
        UPDATE audios
        SET file_url = REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(file_url, 'http://localhost:8000/static/', '/api/v1/files/'),
                    'http://localhost/static/', '/api/v1/files/'
                ),
                'https://localhost:8000/static/', '/api/v1/files/'
            ),
            'https://localhost/static/', '/api/v1/files/'
        )
        WHERE file_url LIKE '%/static/%'
    """)


def downgrade() -> None:
    # 인덱스 삭제
    op.drop_index('ix_books_visibility', table_name='books')
    op.drop_index('ix_books_is_public', table_name='books')
    
    # 컬럼 삭제
    op.drop_column('books', 'visibility')
    op.drop_column('books', 'is_public')
    
    # URL 롤백 (필요 시)
    # op.execute("""
    #     UPDATE pages
    #     SET image_url = REPLACE(image_url, '/api/v1/files/', 'http://localhost:8000/static/')
    #     WHERE image_url LIKE '/api/v1/files/%'
    # """)
    # ... 다른 테이블도 동일하게 ...

