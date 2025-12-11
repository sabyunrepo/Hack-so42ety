"""
공통 책 등록 및 경로 업데이트

Revision ID: 007_migrate_shared_books
Revises: 006_add_book_visibility_and_migrate_urls
Create Date: 2025-12-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    1. 시스템 사용자 생성
    2. 공통 책 등록 (is_default=True, is_public=True, visibility='public')
    3. 파일 경로 업데이트 (shared/books/ 경로로)
    """
    
    # 1. 시스템 사용자 생성
    system_user_id = str(uuid.UUID('00000000-0000-0000-0000-000000000001'))
    
    op.execute(f"""
        INSERT INTO users (id, email, is_active, created_at, updated_at)
        VALUES (
            '{system_user_id}'::uuid,
            'system@moriai.ai',
            true,
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO NOTHING;
    """)
    
    # 2. 공통 책 1: My Playground Day
    book_1_id = '1c8e135a-8e4a-46fb-ac24-13baaacfd586'
    
    op.execute(f"""
        INSERT INTO books (id, user_id, title, cover_image, status, is_default, is_public, visibility, created_at, updated_at)
        VALUES (
            '{book_1_id}'::uuid,
            '{system_user_id}'::uuid,
            'My Playground Day',
            '/api/v1/files/shared/books/{book_1_id}/images/0_page_1.png',
            'completed',
            true,
            true,
            'public',
            '2025-11-01T14:19:40.486916'::timestamp,
            NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            is_default = EXCLUDED.is_default,
            is_public = EXCLUDED.is_public,
            visibility = EXCLUDED.visibility,
            cover_image = EXCLUDED.cover_image,
            updated_at = NOW();
    """)
    
    # 책 1의 페이지 등록
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
            INSERT INTO pages (id, book_id, sequence, image_url, created_at, updated_at)
            VALUES (
                '{page['id']}'::uuid,
                '{book_1_id}'::uuid,
                {page['sequence']},
                '{page['image_url']}',
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                image_url = EXCLUDED.image_url,
                updated_at = NOW();
        """)
    
    # 책 1의 대화 및 오디오 등록
    dialogues_book_1 = [
        {
            'id': '0fd5f91b-324b-4490-b99b-1cb1c60e07b9',
            'page_id': 'f4fe37c1-876b-4628-a3a4-f92112c96b26',
            'sequence': 1,
            'speaker': 'Narrator',
            'text': 'I am at the playground. With my friends. It is hot. I drink water. Gulp, gulp!',
            'audio_url': '/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/audios/page_1_dialogue_1.mp3',
        },
        {
            'id': 'bff6d8f3-21d3-4ea5-bfb5-8e2da80bcdb8',
            'page_id': 'd2fc4c22-762f-44f9-904a-9d887718b5b0',
            'sequence': 1,
            'speaker': 'Narrator',
            'text': 'We play hanging. I hang strong! Wow, I am strong!',
            'audio_url': '/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/audios/page_2_dialogue_1.mp3',
        },
        {
            'id': '89eca997-b44f-4c7f-a8f4-41d422a81314',
            'page_id': 'e4e92c8b-2654-4da5-8116-60325b599785',
            'sequence': 1,
            'speaker': 'Narrator',
            'text': 'We play with bubbles. Pop, pop, pop! So many bubbles. Fun, fun, fun!',
            'audio_url': '/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/audios/page_3_dialogue_1.mp3',
        },
        {
            'id': '748c9d28-ec0b-41f6-9839-de52848d5157',
            'page_id': '418dcd35-92b8-4399-a109-f3e37d536f2c',
            'sequence': 1,
            'speaker': 'Narrator',
            'text': 'I ride the swing. Up and down. I try to swing alone. Whee! So fun!',
            'audio_url': '/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/audios/page_4_dialogue_1.mp3',
        },
        {
            'id': '9f332b2a-9193-45a2-98fb-791da0e60a2d',
            'page_id': '1b486846-cfe8-4b17-aeeb-23b01fd82c07',
            'sequence': 1,
            'speaker': 'Narrator',
            'text': 'I look at bugs. With a magnifying glass. Wow! A bug. So cool!',
            'audio_url': '/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/audios/page_5_dialogue_1.mp3',
        },
    ]
    
    for dialogue in dialogues_book_1:
        # 대화 등록
        op.execute(f"""
            INSERT INTO dialogues (id, page_id, sequence, speaker, created_at, updated_at)
            VALUES (
                '{dialogue['id']}'::uuid,
                '{dialogue['page_id']}'::uuid,
                {dialogue['sequence']},
                '{dialogue['speaker']}',
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                updated_at = NOW();
        """)
        
        # 대화 번역 등록 (영어)
        op.execute(f"""
            INSERT INTO dialogue_translations (id, dialogue_id, language_code, text, is_primary, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                '{dialogue['id']}'::uuid,
                'en',
                '{dialogue['text'].replace("'", "''")}',
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (dialogue_id, language_code) DO UPDATE SET
                text = EXCLUDED.text,
                updated_at = NOW();
        """)
        
        # 대화 오디오 등록
        op.execute(f"""
            INSERT INTO dialogue_audios (id, dialogue_id, language_code, voice_id, audio_url, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                '{dialogue['id']}'::uuid,
                'en',
                'uzyfnLLlKo55AbgBU5uH',
                '{dialogue['audio_url']}',
                NOW(),
                NOW()
            )
            ON CONFLICT (dialogue_id, language_code, voice_id) DO UPDATE SET
                audio_url = EXCLUDED.audio_url,
                updated_at = NOW();
        """)
    
    # 3. 공통 책 2: My Mountain Adventure
    book_2_id = '32e543c7-a845-4cfb-a93d-a0153dc9e063'
    
    op.execute(f"""
        INSERT INTO books (id, user_id, title, cover_image, status, is_default, is_public, visibility, created_at, updated_at)
        VALUES (
            '{book_2_id}'::uuid,
            '{system_user_id}'::uuid,
            'My Mountain Adventure',
            '/api/v1/files/shared/books/{book_2_id}/images/0_page_1.png',
            'completed',
            true,
            true,
            'public',
            NOW(),
            NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            is_default = EXCLUDED.is_default,
            is_public = EXCLUDED.is_public,
            visibility = EXCLUDED.visibility,
            cover_image = EXCLUDED.cover_image,
            updated_at = NOW();
    """)
    
    # 책 2의 페이지는 metadata.json에서 읽어와야 하지만, 
    # 간단히 4개 페이지만 등록 (실제로는 스크립트로 처리)
    pages_book_2 = [
        {
            'id': str(uuid.uuid4()),
            'sequence': 1,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/0_page_1.png',
        },
        {
            'id': str(uuid.uuid4()),
            'sequence': 2,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/1_page_2.png',
        },
        {
            'id': str(uuid.uuid4()),
            'sequence': 3,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/2_page_3.png',
        },
        {
            'id': str(uuid.uuid4()),
            'sequence': 4,
            'image_url': f'/api/v1/files/shared/books/{book_2_id}/images/3_page_4.png',
        },
    ]
    
    for page in pages_book_2:
        op.execute(f"""
            INSERT INTO pages (id, book_id, sequence, image_url, created_at, updated_at)
            VALUES (
                '{page['id']}'::uuid,
                '{book_2_id}'::uuid,
                {page['sequence']},
                '{page['image_url']}',
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO NOTHING;
        """)


def downgrade() -> None:
    """
    마이그레이션 롤백:
    - 공통 책 삭제
    - 시스템 사용자 삭제
    """
    # 1. 공통 책 삭제 (CASCADE로 pages, dialogues도 삭제됨)
    op.execute("""
        DELETE FROM books 
        WHERE id IN (
            '1c8e135a-8e4a-46fb-ac24-13baaacfd586'::uuid,
            '32e543c7-a845-4cfb-a93d-a0153dc9e063'::uuid
        );
    """)
    
    # 2. 시스템 사용자 삭제
    op.execute("""
        DELETE FROM users 
        WHERE id = '00000000-0000-0000-0000-000000000001'::uuid;
    """)

