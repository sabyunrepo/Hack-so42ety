"""
VoiceSyncQueue 단위 테스트
"""
import pytest
import uuid
from backend.core.tasks.voice_queue import VoiceSyncQueue


@pytest.fixture
async def clean_queue():
    """테스트 전후 큐 초기화"""
    queue = VoiceSyncQueue()
    await queue.clear()  # 테스트 전 초기화
    yield queue
    await queue.clear()  # 테스트 후 정리
    await queue.close()


@pytest.mark.asyncio
async def test_voice_queue_enqueue_dequeue(clean_queue):
    """Voice 큐 추가/제거 테스트"""
    queue = clean_queue
    
    voice_id = uuid.uuid4()
    
    # 작업 추가
    result = await queue.enqueue(voice_id)
    assert result is True
    
    # 작업 개수 확인
    count = await queue.count()
    assert count == 1
    
    # 작업 목록 확인
    all_items = await queue.get_all()
    assert str(voice_id) in all_items
    
    # 작업 제거
    result = await queue.dequeue(voice_id)
    assert result is True
    
    # 작업 개수 확인
    count = await queue.count()
    assert count == 0


@pytest.mark.asyncio
async def test_voice_queue_multiple_items(clean_queue):
    """여러 작업 추가 테스트"""
    queue = clean_queue
    
    voice_ids = [uuid.uuid4() for _ in range(5)]
    
    # 여러 작업 추가
    for voice_id in voice_ids:
        await queue.enqueue(voice_id)
    
    # 작업 개수 확인
    count = await queue.count()
    assert count == 5
    
    # 작업 목록 확인
    all_items = await queue.get_all()
    assert len(all_items) == 5
    for voice_id in voice_ids:
        assert str(voice_id) in all_items


@pytest.mark.asyncio
async def test_voice_queue_clear(clean_queue):
    """큐 초기화 테스트"""
    queue = clean_queue
    
    # 작업 추가
    voice_ids = [uuid.uuid4() for _ in range(3)]
    for voice_id in voice_ids:
        await queue.enqueue(voice_id)
    
    assert await queue.count() == 3
    
    # 큐 초기화
    cleared_count = await queue.clear()
    assert cleared_count == 3
    
    # 큐가 비어있는지 확인
    assert await queue.count() == 0

