# ElevenLabs Voice 동기화 전략 (업데이트)

## 🔍 ElevenLabs 웹훅 지원 여부 확인 결과

### ✅ 웹훅 지원 여부
**ElevenLabs는 웹훅을 지원하지만, Voice Clone 생성 완료 웹훅은 제공하지 않습니다.**

### 지원되는 웹훅 이벤트
ElevenLabs에서 현재 지원하는 웹훅 이벤트:

1. **`post_call_transcription`**
   - 에이전트 플랫폼에서 통화가 완료되고 분석이 완료되었을 때 트리거
   - Voice Clone과 무관

2. **`voice_removal_notice`**
   - 공유된 보이스가 제거될 예정일 때 트리거
   - Voice Clone 생성과 무관

3. **`voice_removal_notice_withdrawn`**
   - 공유된 보이스의 제거 예정이 철회되었을 때 트리거
   - Voice Clone 생성과 무관

4. **`voice_removed`**
   - 공유된 보이스가 제거되어 더 이상 사용할 수 없을 때 트리거
   - Voice Clone 생성과 무관

### ❌ 미지원 웹훅 이벤트
- **Voice Clone 생성 완료 웹훅**: 없음
- **Voice Clone 상태 변경 웹훅**: 없음

### 결론
**Voice Clone 생성 완료를 확인하려면 폴링(Polling) 방식이 필수입니다.**

---

## 🎯 최종 권장사항 (업데이트)

### Option 3: Scheduled Task (강력 권장) ⭐⭐⭐⭐⭐

#### 이유
1. **웹훅 미지원으로 폴링 필수**
2. 구현 간단
3. 서버 재시작 시에도 작업 유지
4. 확장 가능
5. 현재 인프라 활용 (Redis, Event Bus)

### Option 2: Redis Queue (확장 시 고려)

#### 전환 시점
- Voice 생성량이 많아질 때
- 더 정밀한 제어가 필요할 때
- 우선순위 큐가 필요할 때

### Option 4: Webhook (현재 불가능) ❌

#### 이유
- **ElevenLabs가 Voice Clone 완료 웹훅을 지원하지 않음**
- 향후 지원 시 전환 고려

---

## 📝 구현 계획 (Option 3 기준)

### Phase 1: DB 모델 수정

```python
class Voice(Base):
    __tablename__ = "voices"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    elevenlabs_voice_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10))
    gender: Mapped[str] = mapped_column(String(20))
    preview_url: Mapped[Optional[str]] = mapped_column(String(1024))
    category: Mapped[str] = mapped_column(String(50))  # premade, cloned, custom
    
    # 상태 관리 필드 추가
    status: Mapped[str] = mapped_column(
        String(20),
        default="processing",  # processing, completed, failed
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 인덱스
    __table_args__ = (
        Index('idx_voice_user_id', 'user_id'),
        Index('idx_voice_status', 'status'),  # 상태별 조회 최적화
        Index('idx_voice_user_status', 'user_id', 'status'),
    )
```

### Phase 2: ElevenLabs Provider에 메서드 추가

```python
async def get_voice_details(self, voice_id: str) -> Dict[str, Any]:
    """
    Voice 상세 정보 조회 (상태 포함)
    
    Args:
        voice_id: ElevenLabs Voice ID
    
    Returns:
        Dict[str, Any]: {
            "voice_id": str,
            "name": str,
            "status": str,  # "processing", "completed", "failed"
            "preview_url": Optional[str],
            "language": str,
            "gender": str,
            ...
        }
    """
    try:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/voices/{voice_id}",
                headers={"xi-api-key": self.api_key},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise TTSAPIAuthenticationFailedException(
                provider="elevenlabs",
                reason="API 키가 유효하지 않거나 만료되었습니다"
            )
        raise TTSGenerationFailedException(
            reason=f"ElevenLabs API 오류: {e.response.status_code} - {e.response.text}"
        )
    except httpx.RequestError as e:
        raise TTSGenerationFailedException(
            reason=f"ElevenLabs API 요청 실패: {str(e)}"
        )
    
    data = response.json()
    
    # ElevenLabs 응답 형식을 표준 형식으로 변환
    # 주의: ElevenLabs API 응답 구조 확인 필요
    return {
        "voice_id": data.get("voice_id"),
        "name": data.get("name"),
        "status": self._parse_voice_status(data),  # "processing", "completed", "failed"
        "preview_url": data.get("preview_url"),
        "language": data.get("labels", {}).get("language", "en"),
        "gender": data.get("labels", {}).get("gender", "unknown"),
        "category": data.get("category", "generated"),
    }

def _parse_voice_status(self, data: dict) -> str:
    """
    ElevenLabs API 응답에서 Voice 상태 파싱
    
    주의: ElevenLabs API 문서 확인 필요
    """
    # 예시: preview_url이 있으면 완료로 간주
    if data.get("preview_url"):
        return "completed"
    
    # 예시: 특정 필드로 상태 확인
    # 실제 API 응답 구조에 맞게 수정 필요
    return "processing"
```

### Phase 3: Scheduled Task 구현

```python
# backend/core/tasks/voice_sync.py
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database.session import get_db
from backend.features.tts.repository import VoiceRepository
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.events.types import EventType

logger = logging.getLogger(__name__)

async def sync_voice_status_periodically(
    db_session: AsyncSession,
    event_bus: RedisStreamsEventBus,
    interval: int = 60,  # 1분마다 실행
    max_age_minutes: int = 30,  # 30분 이상 오래된 "processing" 상태는 실패 처리
):
    """
    주기적으로 Voice 상태 동기화
    
    Args:
        db_session: 데이터베이스 세션
        event_bus: 이벤트 버스
        interval: 실행 간격 (초)
        max_age_minutes: 최대 대기 시간 (분)
    """
    while True:
        try:
            await asyncio.sleep(interval)
            
            logger.info("Starting voice status sync...")
            
            # "processing" 상태인 모든 Voice 조회
            voice_repo = VoiceRepository(db_session)
            processing_voices = await voice_repo.get_by_status("processing")
            
            if not processing_voices:
                logger.debug("No processing voices found")
                continue
            
            logger.info(f"Found {len(processing_voices)} processing voices")
            
            # AI Factory 및 TTS Provider 초기화
            ai_factory = AIProviderFactory()
            tts_provider = ai_factory.get_tts_provider()
            
            for voice in processing_voices:
                try:
                    # 생성 후 경과 시간 확인
                    age_minutes = (datetime.utcnow() - voice.created_at).total_seconds() / 60
                    if age_minutes > max_age_minutes:
                        logger.warning(
                            f"Voice {voice.id} exceeded max age ({age_minutes:.1f} minutes), "
                            f"marking as failed"
                        )
                        await voice_repo.update(
                            voice_id=voice.id,
                            status="failed",
                        )
                        continue
                    
                    # ElevenLabs API에서 Voice 상세 정보 조회
                    voice_details = await tts_provider.get_voice_details(
                        voice.elevenlabs_voice_id
                    )
                    
                    # 완료 확인
                    if voice_details.get("status") == "completed":
                        logger.info(f"Voice {voice.id} completed, updating database")
                        
                        await voice_repo.update(
                            voice_id=voice.id,
                            preview_url=voice_details.get("preview_url"),
                            status="completed",
                            completed_at=datetime.utcnow(),
                        )
                        
                        # 이벤트 발행 (캐시 무효화)
                        await event_bus.publish(
                            EventType.VOICE_CREATED,
                            {
                                "voice_id": str(voice.id),
                                "user_id": str(voice.user_id),
                            }
                        )
                        
                        logger.info(f"Voice {voice.id} sync completed")
                    
                    # 실패 확인
                    elif voice_details.get("status") == "failed":
                        logger.warning(f"Voice {voice.id} failed")
                        
                        await voice_repo.update(
                            voice_id=voice.id,
                            status="failed",
                        )
                    
                    # 아직 처리 중
                    else:
                        logger.debug(f"Voice {voice.id} still processing")
                        
                except Exception as e:
                    logger.error(
                        f"Error syncing voice {voice.id}: {e}",
                        exc_info=True
                    )
                    # 개별 Voice 동기화 실패는 계속 진행
            
            await db_session.commit()
            logger.info("Voice status sync completed")
            
        except Exception as e:
            logger.error(f"Voice sync task error: {e}", exc_info=True)
            await asyncio.sleep(interval)
```

### Phase 4: lifespan에 Scheduled Task 추가

```python
# backend/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus
    
    # ... 기존 startup 코드 ...
    
    # Voice 동기화 작업 시작
    from backend.core.tasks.voice_sync import sync_voice_status_periodically
    from backend.core.database.session import get_db
    
    # DB 세션 및 Event Bus 전달
    async for db_session in get_db():
        sync_task = asyncio.create_task(
            sync_voice_status_periodically(
                db_session=db_session,
                event_bus=event_bus,
                interval=60,  # 1분마다 실행
            )
        )
        break  # 첫 번째 세션만 사용
    
    yield
    
    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
```

### Phase 5: Voice 생성 로직 수정

```python
# backend/features/tts/service.py
async def create_voice_clone(
    self,
    user_id: uuid.UUID,
    name: str,
    audio_file: bytes,
) -> Dict[str, Any]:
    """
    Voice Clone 생성
    
    생성 후 Scheduled Task가 자동으로 상태 동기화
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
        name=elevenlabs_voice["name"],
        language=elevenlabs_voice.get("language", "en"),
        gender=elevenlabs_voice.get("gender", "unknown"),
        category="cloned",
        status="processing",  # 초기 상태
        preview_url=None,  # 아직 없음
    )
    
    # Scheduled Task가 자동으로 상태 동기화
    # 별도 백그라운드 작업 불필요
    
    return voice
```

---

## ✅ 구현 체크리스트

- [ ] Voice 모델에 `status`, `preview_url`, `completed_at` 필드 추가
- [ ] 마이그레이션 작성
- [ ] `ElevenLabsTTSProvider.get_voice_details()` 구현
- [ ] `sync_voice_status_periodically()` 함수 구현
- [ ] `lifespan`에 Scheduled Task 추가
- [ ] `create_voice_clone()` 수정 (status="processing")
- [ ] 테스트 작성
- [ ] 로깅 추가
- [ ] 에러 처리 강화

---

## 📚 참고 자료

- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Redis Queue 패턴
- ElevenLabs API 문서: https://elevenlabs.io/docs/api-reference
- **ElevenLabs 웹훅 문서**: https://elevenlabs.io/docs/product-guides/administration/webhooks
  - **중요**: Voice Clone 완료 웹훅은 지원하지 않음

