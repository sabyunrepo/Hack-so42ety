# Voice 사용자별 관리 구현 계획 (Redis 최적화 버전)

## 📋 최적화 아이디어

### 기존 방식의 문제점
- Scheduled Task가 매번 DB에서 "processing" 상태 Voice를 모두 조회
- 처리할 작업이 없어도 DB 쿼리 실행
- 비효율적인 리소스 사용

### 최적화된 방식
1. **Voice 생성 시 Redis에 작업 정보 저장**
   - Redis Set 또는 Sorted Set에 작업 ID 저장
   - TTL 설정 (예: 30분)

2. **Scheduled Task 최적화**
   - Redis에 작업이 있을 때만 실행
   - Redis에서 작업 ID 목록 조회
   - 해당 작업만 DB에서 조회 및 처리

3. **필터링 최적화**
   - Redis에 등록된 작업만 처리
   - 불필요한 DB 쿼리 감소

---

## 🎯 최적화된 구현 계획

### Phase 1: DB 모델 및 마이그레이션
- Voice 모델 생성
- 마이그레이션 작성
- 테스트 작성
- 스테이징 커밋

### Phase 2: Redis 작업 큐 구현
- Voice 작업 큐 클래스 구현
- 작업 추가/제거 메서드
- 테스트 작성
- 스테이징 커밋

### Phase 3: Repository 및 Service 레이어
- VoiceRepository 구현
- TTSService 수정 (Redis 큐 통합)
- 테스트 작성
- 스테이징 커밋

### Phase 4: ElevenLabs Provider 확장
- `get_voice_details()` 메서드 추가
- 테스트 작성
- 스테이징 커밋

### Phase 5: Scheduled Task 구현 (최적화)
- Redis 기반 작업 조회
- 필터링된 작업만 처리
- 테스트 작성
- 스테이징 커밋

### Phase 6: API 엔드포인트 수정
- 사용자별 Voice 조회 로직
- 테스트 작성
- 스테이징 커밋

### Phase 7: 통합 테스트 및 최종 검증
- 전체 플로우 테스트
- 성능 테스트
- 문서 업데이트
- 스테이징 커밋

---

## 📝 Phase 2: Redis 작업 큐 구현 (새로 추가)

### 2.1 Voice 작업 큐 클래스

**파일**: `backend/core/tasks/voice_queue.py` (새로 생성)

```python
"""
Voice 동기화 작업 큐 (Redis 기반)
Voice 생성 시 Redis에 작업 정보 저장, Scheduled Task에서 조회
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Set
import redis.asyncio as aioredis
from backend.core.config import settings

logger = logging.getLogger(__name__)


class VoiceSyncQueue:
    """
    Voice 동기화 작업 큐 (Redis 기반)
    
    Redis Set을 사용하여 처리 대기 중인 Voice ID 저장
    - Key: "voice:sync:queue"
    - Value: Set of voice_id (UUID string)
    - TTL: 30분 (자동 만료)
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.queue_key = "voice:sync:queue"
        self.ttl_seconds = 30 * 60  # 30분
    
    async def connect(self):
        """Redis 연결"""
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def enqueue(self, voice_id: uuid.UUID) -> bool:
        """
        Voice 동기화 작업 추가
        
        Args:
            voice_id: Voice UUID
        
        Returns:
            bool: 추가 성공 여부
        """
        await self.connect()
        
        try:
            voice_id_str = str(voice_id)
            
            # Set에 추가
            await self.redis.sadd(self.queue_key, voice_id_str)
            
            # TTL 설정 (큐 자체는 영구, 개별 항목은 처리 시 제거)
            await self.redis.expire(self.queue_key, self.ttl_seconds)
            
            logger.info(f"Voice {voice_id} added to sync queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue voice {voice_id}: {e}", exc_info=True)
            return False
    
    async def dequeue(self, voice_id: uuid.UUID) -> bool:
        """
        Voice 동기화 작업 제거 (처리 완료 시)
        
        Args:
            voice_id: Voice UUID
        
        Returns:
            bool: 제거 성공 여부
        """
        await self.connect()
        
        try:
            voice_id_str = str(voice_id)
            removed = await self.redis.srem(self.queue_key, voice_id_str)
            
            if removed:
                logger.info(f"Voice {voice_id} removed from sync queue")
            
            return removed > 0
            
        except Exception as e:
            logger.error(f"Failed to dequeue voice {voice_id}: {e}", exc_info=True)
            return False
    
    async def get_all(self) -> Set[str]:
        """
        모든 대기 중인 작업 조회
        
        Returns:
            Set[str]: Voice ID 문자열 집합
        """
        await self.connect()
        
        try:
            voice_ids = await self.redis.smembers(self.queue_key)
            return voice_ids if voice_ids else set()
            
        except Exception as e:
            logger.error(f"Failed to get queue items: {e}", exc_info=True)
            return set()
    
    async def count(self) -> int:
        """
        대기 중인 작업 개수 조회
        
        Returns:
            int: 작업 개수
        """
        await self.connect()
        
        try:
            return await self.redis.scard(self.queue_key)
            
        except Exception as e:
            logger.error(f"Failed to get queue count: {e}", exc_info=True)
            return 0
    
    async def clear(self) -> int:
        """
        모든 작업 제거 (테스트용)
        
        Returns:
            int: 제거된 작업 개수
        """
        await self.connect()
        
        try:
            count = await self.count()
            await self.redis.delete(self.queue_key)
            return count
            
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}", exc_info=True)
            return 0
    
    async def close(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            self.redis = None
```

### 2.2 테스트 작성

**파일**: `backend/tests/unit/tasks/test_voice_queue.py`

```python
import pytest
import uuid
from backend.core.tasks.voice_queue import VoiceSyncQueue


@pytest.mark.asyncio
async def test_voice_queue_enqueue_dequeue():
    """Voice 큐 추가/제거 테스트"""
    queue = VoiceSyncQueue()
    
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
    
    await queue.close()


@pytest.mark.asyncio
async def test_voice_queue_multiple_items():
    """여러 작업 추가 테스트"""
    queue = VoiceSyncQueue()
    
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
    
    await queue.close()
```

### 2.3 Phase 2 완료 체크리스트
- [ ] VoiceSyncQueue 클래스 구현
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 3: Repository 및 Service 레이어 (수정)

### 3.1 TTSService 수정 (Redis 큐 통합)

**파일**: `backend/features/tts/service.py`

```python
from backend.core.tasks.voice_queue import VoiceSyncQueue

class TTSService:
    def __init__(
        self,
        audio_repo: AudioRepository,
        voice_repo: VoiceRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
        cache_service,
        event_bus: EventBus,
    ):
        self.audio_repo = audio_repo
        self.voice_repo = voice_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session
        self.cache_service = cache_service
        self.event_bus = event_bus
        self.voice_queue = VoiceSyncQueue()  # 추가

    async def create_voice_clone(
        self,
        user_id: uuid.UUID,
        name: str,
        audio_file: bytes,
        visibility: VoiceVisibility = VoiceVisibility.PRIVATE,
    ) -> Voice:
        """
        Voice Clone 생성
        
        생성 후 Redis 큐에 작업 추가
        """
        # ElevenLabs API 호출
        tts_provider = self.ai_factory.get_tts_provider()
        elevenlabs_voice = await tts_provider.clone_voice(
            name=name,
            audio_file=audio_file
        )
        
        # DB에 "processing" 상태로 저장
        voice = await self.voice_repo.create(
            user_id=user_id,
            elevenlabs_voice_id=elevenlabs_voice["voice_id"],
            name=elevenlabs_voice.get("name", name),
            language=elevenlabs_voice.get("language", "en"),
            gender=elevenlabs_voice.get("gender", "unknown"),
            category="cloned",
            visibility=visibility,
            status=VoiceStatus.PROCESSING,
            preview_url=None,
        )
        
        # Redis 큐에 작업 추가
        await self.voice_queue.enqueue(voice.id)
        
        logger.info(f"Voice {voice.id} created and added to sync queue")
        
        return voice
```

### 3.2 Phase 3 완료 체크리스트
- [ ] VoiceRepository 구현
- [ ] TTSService 수정 (Redis 큐 통합)
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 5: Scheduled Task 구현 (최적화)

### 5.1 최적화된 Scheduled Task

**파일**: `backend/core/tasks/voice_sync.py`

```python
"""
Voice 동기화 Scheduled Task (Redis 최적화)
Redis 큐에 등록된 작업만 처리
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.tts.repository import VoiceRepository
from backend.features.tts.models import VoiceStatus
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.events.types import EventType
from backend.core.tasks.voice_queue import VoiceSyncQueue
from backend.core.database.session import get_db

logger = logging.getLogger(__name__)


async def sync_voice_status_periodically(
    event_bus: RedisStreamsEventBus,
    interval: int = 60,  # 1분마다 실행
    max_age_minutes: int = 30,  # 30분 이상 오래된 "processing" 상태는 실패 처리
):
    """
    주기적으로 Voice 상태 동기화 (Redis 최적화)
    
    Redis 큐에 등록된 작업만 처리하여 효율성 향상
    
    Args:
        event_bus: 이벤트 버스
        interval: 실행 간격 (초)
        max_age_minutes: 최대 대기 시간 (분)
    """
    voice_queue = VoiceSyncQueue()
    
    while True:
        try:
            await asyncio.sleep(interval)
            
            # Redis 큐에서 대기 중인 작업 조회
            queued_voice_ids = await voice_queue.get_all()
            
            if not queued_voice_ids:
                logger.debug("No voices in sync queue, skipping")
                continue
            
            logger.info(f"Found {len(queued_voice_ids)} voices in sync queue")
            
            # DB 세션 생성
            async for db_session in get_db():
                try:
                    voice_repo = VoiceRepository(db_session)
                    ai_factory = AIProviderFactory()
                    tts_provider = ai_factory.get_tts_provider()
                    
                    # Redis 큐에 등록된 Voice만 조회
                    voice_ids = [uuid.UUID(vid) for vid in queued_voice_ids]
                    
                    # DB에서 해당 Voice들만 조회 (필터링)
                    voices = []
                    for voice_id in voice_ids:
                        voice = await voice_repo.get(voice_id)
                        if voice and voice.status == VoiceStatus.PROCESSING:
                            voices.append(voice)
                    
                    if not voices:
                        logger.debug("No processing voices found in queue")
                        # 큐 정리 (이미 완료된 작업 제거)
                        for voice_id_str in queued_voice_ids:
                            await voice_queue.dequeue(uuid.UUID(voice_id_str))
                        continue
                    
                    logger.info(f"Processing {len(voices)} voices from queue")
                    
                    # 각 Voice 상태 확인 및 업데이트
                    for voice in voices:
                        try:
                            # 생성 후 경과 시간 확인
                            age_minutes = (datetime.utcnow() - voice.created_at).total_seconds() / 60
                            if age_minutes > max_age_minutes:
                                logger.warning(
                                    f"Voice {voice.id} exceeded max age ({age_minutes:.1f} minutes), "
                                    f"marking as failed"
                                )
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.FAILED,
                                )
                                # 큐에서 제거
                                await voice_queue.dequeue(voice.id)
                                continue
                            
                            # ElevenLabs API에서 Voice 상세 정보 조회
                            voice_details = await tts_provider.get_voice_details(
                                voice.elevenlabs_voice_id
                            )
                            
                            # 완료 확인
                            if voice_details.get("status") == "completed":
                                logger.info(f"Voice {voice.id} completed, updating database")
                                
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.COMPLETED,
                                    preview_url=voice_details.get("preview_url"),
                                )
                                
                                # 이벤트 발행 (캐시 무효화)
                                await event_bus.publish(
                                    EventType.VOICE_CREATED,
                                    {
                                        "voice_id": str(voice.id),
                                        "user_id": str(voice.user_id),
                                    }
                                )
                                
                                # 큐에서 제거
                                await voice_queue.dequeue(voice.id)
                                
                                logger.info(f"Voice {voice.id} sync completed and removed from queue")
                            
                            # 실패 확인
                            elif voice_details.get("status") == "failed":
                                logger.warning(f"Voice {voice.id} failed")
                                
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.FAILED,
                                )
                                
                                # 큐에서 제거
                                await voice_queue.dequeue(voice.id)
                            
                            # 아직 처리 중
                            else:
                                logger.debug(f"Voice {voice.id} still processing")
                                # 큐에 유지 (다음 주기에 다시 확인)
                                
                        except Exception as e:
                            logger.error(
                                f"Error syncing voice {voice.id}: {e}",
                                exc_info=True
                            )
                            # 개별 Voice 동기화 실패는 계속 진행
                            # 큐에는 유지 (재시도)
                    
                    await db_session.commit()
                    logger.info("Voice status sync completed")
                    
                except Exception as e:
                    logger.error(f"Voice sync task error: {e}", exc_info=True)
                    await db_session.rollback()
                finally:
                    await db_session.close()
                break  # 첫 번째 세션만 사용
            
        except Exception as e:
            logger.error(f"Voice sync task error: {e}", exc_info=True)
            await asyncio.sleep(interval)
        finally:
            # 정리 작업은 각 Voice 처리 시 수행
            pass
```

### 5.2 최적화 효과

#### 기존 방식
```python
# 매번 DB에서 모든 "processing" 상태 Voice 조회
processing_voices = await voice_repo.get_by_status(VoiceStatus.PROCESSING)
# → 처리할 작업이 없어도 DB 쿼리 실행
```

#### 최적화된 방식
```python
# Redis 큐에 등록된 작업만 조회
queued_voice_ids = await voice_queue.get_all()
if not queued_voice_ids:
    return  # 작업이 없으면 즉시 종료

# Redis 큐에 등록된 Voice만 DB에서 조회
voices = [await voice_repo.get(vid) for vid in queued_voice_ids]
# → 처리할 작업이 있을 때만 DB 쿼리 실행
```

### 5.3 성능 비교

| 항목 | 기존 방식 | 최적화된 방식 |
|------|----------|--------------|
| **DB 쿼리 빈도** | 매번 실행 | 작업이 있을 때만 |
| **Redis 조회** | 없음 | O(1) Set 조회 |
| **처리 효율** | 낮음 | 높음 |
| **리소스 사용** | 높음 | 낮음 |

### 5.4 Phase 5 완료 체크리스트
- [ ] 최적화된 Scheduled Task 구현
- [ ] Redis 큐 통합
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📊 최적화 전후 비교

### 기존 방식
1. Scheduled Task 실행 (1분마다)
2. DB에서 모든 "processing" 상태 Voice 조회
3. 각 Voice 상태 확인
4. 완료 시 DB 업데이트

**문제점**:
- 처리할 작업이 없어도 DB 쿼리 실행
- 불필요한 리소스 사용

### 최적화된 방식
1. Voice 생성 시 Redis 큐에 작업 추가
2. Scheduled Task 실행 (1분마다)
3. **Redis 큐 확인 → 작업이 없으면 즉시 종료**
4. **Redis 큐에 등록된 Voice만 DB에서 조회**
5. 각 Voice 상태 확인
6. 완료 시 DB 업데이트 및 큐에서 제거

**장점**:
- 처리할 작업이 없으면 즉시 종료
- 필요한 Voice만 DB에서 조회
- Redis Set 조회는 O(1)로 매우 빠름
- 리소스 사용 최소화

---

## ✅ 최종 구현 체크리스트

### Phase 1: DB 모델 및 마이그레이션
- [ ] Voice 모델 생성
- [ ] 마이그레이션 작성
- [ ] 테스트 작성
- [ ] 스테이징 커밋

### Phase 2: Redis 작업 큐 구현 (새로 추가)
- [ ] VoiceSyncQueue 클래스 구현
- [ ] 테스트 작성
- [ ] 스테이징 커밋

### Phase 3: Repository 및 Service 레이어
- [ ] VoiceRepository 구현
- [ ] TTSService 수정 (Redis 큐 통합)
- [ ] 테스트 작성
- [ ] 스테이징 커밋

### Phase 4: ElevenLabs Provider 확장
- [ ] `get_voice_details()` 구현
- [ ] 테스트 작성
- [ ] 스테이징 커밋

### Phase 5: Scheduled Task 구현 (최적화)
- [ ] Redis 기반 작업 조회
- [ ] 필터링된 작업만 처리
- [ ] 테스트 작성
- [ ] 스테이징 커밋

### Phase 6: API 엔드포인트 수정
- [ ] 사용자별 Voice 조회 로직
- [ ] 테스트 작성
- [ ] 스테이징 커밋

### Phase 7: 통합 테스트 및 최종 검증
- [ ] 전체 플로우 테스트
- [ ] 성능 테스트
- [ ] 문서 업데이트
- [ ] 스테이징 커밋

---

## 🎯 최적화 요약

### 핵심 개선 사항
1. **Redis 작업 큐 도입**
   - Voice 생성 시 Redis에 작업 정보 저장
   - Scheduled Task는 Redis 큐만 확인

2. **조건부 실행**
   - Redis 큐에 작업이 있을 때만 DB 쿼리 실행
   - 작업이 없으면 즉시 종료

3. **필터링 최적화**
   - Redis 큐에 등록된 Voice만 DB에서 조회
   - 불필요한 DB 쿼리 감소

### 성능 향상
- **DB 쿼리 감소**: 작업이 없을 때 0회
- **Redis 조회**: O(1) Set 조회로 매우 빠름
- **리소스 사용**: 최소화

---

## 📝 다음 단계

Phase 1부터 시작할까요? 각 페이즈 완료 시 테스트를 실행하고 스테이징에 커밋하겠습니다.

