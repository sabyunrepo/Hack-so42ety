"""
공통 책 파일 접근 테스트
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shared_book_image_access_without_auth(async_client: AsyncClient):
    """공통 책 이미지는 인증 없이 접근 가능"""
    # 공통 책 이미지 접근
    response = await async_client.get(
        "/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/images/0_page_1.png"
    )
    
    # 파일이 존재하지 않아도 403이 아닌 404가 반환되어야 함 (접근 권한은 있음)
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_shared_book_audio_access_without_auth(async_client: AsyncClient):
    """공통 책 오디오는 인증 없이 접근 가능"""
    # 공통 책 오디오 접근
    response = await async_client.get(
        "/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/audios/page_1_dialogue_1.mp3"
    )
    
    # 파일이 존재하지 않아도 403이 아닌 404가 반환되어야 함 (접근 권한은 있음)
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_shared_book_video_access_without_auth(async_client: AsyncClient):
    """공통 책 비디오는 인증 없이 접근 가능"""
    # 공통 책 비디오 접근
    response = await async_client.get(
        "/api/v1/files/shared/books/1c8e135a-8e4a-46fb-ac24-13baaacfd586/videos/page_1.mp4"
    )
    
    # 파일이 존재하지 않아도 403이 아닌 404가 반환되어야 함 (접근 권한은 있음)
    assert response.status_code in [200, 404]

