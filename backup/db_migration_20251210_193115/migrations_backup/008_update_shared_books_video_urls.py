"""
공통 책 비디오 URL 업데이트

Revision ID: 008_update_shared_books_video_urls
Revises: 007_migrate_shared_books
Create Date: 2025-12-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    공통 책의 image_url을 비디오 URL로 업데이트
    
    image_url 필드를 "미디어 URL"로 재해석하여 비디오/이미지 모두 지원
    프론트엔드는 URL 확장자로 자동 판단 (.mp4 → video, 나머지 → image)
    """
    
    # ==================== Book 1: My Playground Day ====================
    book_1_id = '1c8e135a-8e4a-46fb-ac24-13baaacfd586'
    
    pages_book_1 = [
        {
            'id': 'f4fe37c1-876b-4628-a3a4-f92112c96b26',
            'sequence': 1,
            'video_url': f'/api/v1/files/shared/books/{book_1_id}/videos/page_1.mp4',
        },
        {
            'id': 'd2fc4c22-762f-44f9-904a-9d887718b5b0',
            'sequence': 2,
            'video_url': f'/api/v1/files/shared/books/{book_1_id}/videos/page_2.mp4',
        },
        {
            'id': 'e4e92c8b-2654-4da5-8116-60325b599785',
            'sequence': 3,
            'video_url': f'/api/v1/files/shared/books/{book_1_id}/videos/page_3.mp4',
        },
        {
            'id': '418dcd35-92b8-4399-a109-f3e37d536f2c',
            'sequence': 4,
            'video_url': f'/api/v1/files/shared/books/{book_1_id}/videos/page_4.mp4',
        },
        {
            'id': '1b486846-cfe8-4b17-aeeb-23b01fd82c07',
            'sequence': 5,
            'video_url': f'/api/v1/files/shared/books/{book_1_id}/videos/page_5.mp4',
        },
    ]
    
    for page in pages_book_1:
        op.execute(f"""
            UPDATE pages 
            SET 
                image_url = '{page['video_url']}',
                updated_at = NOW()
            WHERE id = '{page['id']}'::uuid;
        """)
    
    # ==================== Book 2: My Mountain Adventure ====================
    book_2_id = '32e543c7-a845-4cfb-a93d-a0153dc9e063'
    
    pages_book_2 = [
        {
            'id': '3baf370f-8f4c-4bef-b091-6c3f2bc34cd4',
            'sequence': 1,
            'video_url': f'/api/v1/files/shared/books/{book_2_id}/videos/page_1.mp4',
        },
        {
            'id': '7e409966-7aa9-4d8c-83a3-d344cba3a120',
            'sequence': 2,
            'video_url': f'/api/v1/files/shared/books/{book_2_id}/videos/page_2.mp4',
        },
        {
            'id': 'ebe3f128-2e74-47e4-ab9a-80c2fffabe5c',
            'sequence': 3,
            'video_url': f'/api/v1/files/shared/books/{book_2_id}/videos/page_3.mp4',
        },
        {
            'id': 'c0129b75-faea-4207-92db-606339c1a89f',
            'sequence': 4,
            'video_url': f'/api/v1/files/shared/books/{book_2_id}/videos/page_4.mp4',
        },
    ]
    
    for page in pages_book_2:
        op.execute(f"""
            UPDATE pages 
            SET 
                image_url = '{page['video_url']}',
                updated_at = NOW()
            WHERE id = '{page['id']}'::uuid;
        """)


def downgrade() -> None:
    """
    롤백: 비디오 URL을 이미지 URL로 복원
    """
    
    # ==================== Book 1: My Playground Day ====================
    book_1_id = '1c8e135a-8e4a-46fb-ac24-13baaacfd586'
    
    pages_book_1 = [
        {
            'id': 'f4fe37c1-876b-4628-a3a4-f92112c96b26',
            'sequence': 1,
            'image_url': f'/api/v1/files/shared/books/{book_1_id}/images/0_page_1.png',
        },
        {
            'id': 'd2fc4c22-762f-44f9-904a-9d887718b5b0',
            'sequence': 2,
            'image_url': f'/api/v1/files/shared/books/{book_1_id}/images/1_page_2.png',
        },
        {
            'id': 'e4e92c8b-2654-4da5-8116-60325b599785',
            'sequence': 3,
            'image_url': f'/api/v1/files/shared/books/{book_1_id}/images/2_page_3.png',
        },
        {
            'id': '418dcd35-92b8-4399-a109-f3e37d536f2c',
            'sequence': 4,
            'image_url': f'/api/v1/files/shared/books/{book_1_id}/images/3_page_4.png',
        },
        {
            'id': '1b486846-cfe8-4b17-aeeb-23b01fd82c07',
            'sequence': 5,
            'image_url': f'/api/v1/files/shared/books/{book_1_id}/images/4_page_5.png',
        },
    ]
    
    for page in pages_book_1:
        op.execute(f"""
            UPDATE pages 
            SET 
                image_url = '{page['image_url']}',
                updated_at = NOW()
            WHERE id = '{page['id']}'::uuid;
        """)
    
    # ==================== Book 2: My Mountain Adventure ====================
    book_2_id = '32e543c7-a845-4cfb-a93d-a0153dc9e063'
    
    pages_book_2 = [
        {
            'id': '3baf370f-8f4c-4bef-b091-6c3f2bc34cd4',
            'sequence': 1,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/0_page_1.png',
        },
        {
            'id': '7e409966-7aa9-4d8c-83a3-d344cba3a120',
            'sequence': 2,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/1_page_2.png',
        },
        {
            'id': 'ebe3f128-2e74-47e4-ab9a-80c2fffabe5c',
            'sequence': 3,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/2_page_3.png',
        },
        {
            'id': 'c0129b75-faea-4207-92db-606339c1a89f',
            'sequence': 4,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/3_page_4.png',
        },
    ]
    
    for page in pages_book_2:
        op.execute(f"""
            UPDATE pages 
            SET 
                image_url = '{page['image_url']}',
                updated_at = NOW()
            WHERE id = '{page['id']}'::uuid;
        """)

