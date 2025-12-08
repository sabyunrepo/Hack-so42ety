# ElevenLabs Voice 동기화 전략

## 📋 문제 상황

ElevenLabs Voice Clone 생성은 **비동기 처리**됩니다:
1. Voice 생성 요청 → ElevenLabs API 호출 → 즉시 `voice_id` 반환
2. 하지만 `preview_url` 등은 **완료 후**에야 제공됨
3. DB에 저장했지만 **미완성 상태**로 저장됨
4. **주기적으로 상태 확인하여 동기화** 필요

---

## 🔍 해결 방안 비교

### Option 1: FastAPI BackgroundTasks (간단) ⭐⭐⭐

#### 구현 방식
- Voice 생성 시 `BackgroundTasks`로 폴링 작업 시작
- 주기적으로 ElevenLabs API 호출하여 상태 확인
- 완료되면 DB 업데이트

#### 장점 ✅
- 구현 간단 (FastAPI 내장)
- 추가 의존성 없음
- 빠른 구현 가능

#### 단점 ❌
- 서버 재시작 시 작업 손실
- 확장성 제한 (단일 프로세스)
- 장기 실행 작업에 부적합

#### 구현 예시
```python
from fastapi import BackgroundTasks

async def create_voice_clone(
    self,
    user_id: uuid.UUID,
    name: str,
    audio_file: bytes,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
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
        status="processing",  # 상태 추가
        preview_url=None,  # 아직 없음
    )
    
    # 백그라운드 작업으로 폴링 시작
    background_tasks.add_task(
        self._poll_voice_status,
        voice_id=voice.id,
        elevenlabs_voice_id=elevenlabs_voice["voice_id"],
    )
    
    return voice

async def _poll_voice_status(
    self,
    voice_id: uuid.UUID,
    elevenlabs_voice_id: str,
    max_attempts: int = 60,  # 최대 5분 (5초 간격)
    interval: int = 5,  # 5초마다 확인
):
    """Voice 상태 폴링"""
    tts_provider = self.ai_factory.get_tts_provider()
    
    for attempt in range(max_attempts):
        await asyncio.sleep(interval)
        
        try:
            # ElevenLabs API에서 Voice 상세 정보 조회
            voice_details = await tts_provider.get_voice_details(elevenlabs_voice_id)
            
            # 완료 확인
            if voice_details.get("status") == "completed":
                # DB 업데이트
                await self.voice_repo.update(
                    voice_id=voice_id,
                    preview_url=voice_details.get("preview_url"),
                    status="completed",
                )
                
                # 이벤트 발행 (캐시 무효화)
                await self.event_bus.publish(
                    EventType.VOICE_CREATED,
                    {"voice_id": str(voice_id), "user_id": str(voice.user_id)}
                )
                return
            
            # 실패 확인
            if voice_details.get("status") == "failed":
                await self.voice_repo.update(
                    voice_id=voice_id,
                    status="failed",
                )
                return
                
        except Exception as e:
            logger.error(f"Voice status polling error: {e}")
            if attempt == max_attempts - 1:
                # 최대 시도 횟수 초과 시 실패 처리
                await self.voice_repo.update(
                    voice_id=voice_id,
                    status="failed",
                )
```

---

### Option 2: Redis Queue + Background Worker (권장) ⭐⭐⭐⭐⭐

#### 구현 방식
- Voice 생성 시 Redis Queue에 작업 추가
- 별도 워커 프로세스가 주기적으로 폴링
- 완료되면 DB 업데이트 및 이벤트 발행

#### 장점 ✅
- 확장 가능 (여러 워커 실행 가능)
- 서버 재시작 시에도 작업 유지 (Redis에 저장)
- 장기 실행 작업 처리 가능
- 작업 재시도 로직 구현 용이

#### 단점 ❌
- 구현 복잡도 높음
- 별도 워커 프로세스 필요
- Redis 의존성

#### 구현 예시
```python
# 1. Redis Queue에 작업 추가
import redis.asyncio as aioredis
from datetime import datetime, timedelta

class VoiceSyncQueue:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.queue_key = "voice:sync:queue"
    
    async def enqueue(self, voice_id: str, elevenlabs_voice_id: str):
        """Voice 동기화 작업 추가"""
        job = {
            "voice_id": voice_id,
            "elevenlabs_voice_id": elevenlabs_voice_id,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0,
            "max_attempts": 60,
        }
        await self.redis.lpush(self.queue_key, json.dumps(job))
    
    async def dequeue(self) -> Optional[dict]:
        """작업 가져오기"""
        result = await self.redis.brpop(self.queue_key, timeout=1)
        if result:
            return json.loads(result[1])
        return None

# 2. Voice 생성 시 Queue에 추가
async def create_voice_clone(
    self,
    user_id: uuid.UUID,
    name: str,
    audio_file: bytes,
) -> Dict[str, Any]:
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
        status="processing",
    )
    
    # Queue에 동기화 작업 추가
    sync_queue = VoiceSyncQueue(settings.redis_url)
    await sync_queue.enqueue(
        voice_id=str(voice.id),
        elevenlabs_voice_id=elevenlabs_voice["voice_id"],
    )
    
    return voice

# 3. 별도 워커 프로세스 (worker.py)
async def voice_sync_worker():
    """Voice 동기화 워커"""
    sync_queue = VoiceSyncQueue(settings.redis_url)
    tts_provider = AIProviderFactory().get_tts_provider()
    
    while True:
        job = await sync_queue.dequeue()
        if not job:
            await asyncio.sleep(1)
            continue
        
        try:
            voice_id = uuid.UUID(job["voice_id"])
            elevenlabs_voice_id = job["elevenlabs_voice_id"]
            attempts = job["attempts"]
            
            # ElevenLabs API에서 Voice 상세 정보 조회
            voice_details = await tts_provider.get_voice_details(elevenlabs_voice_id)
            
            # 완료 확인
            if voice_details.get("status") == "completed":
                # DB 업데이트
                voice_repo = VoiceRepository(db_session)
                await voice_repo.update(
                    voice_id=voice_id,
                    preview_url=voice_details.get("preview_url"),
                    status="completed",
                )
                
                # 이벤트 발행
                event_bus.publish(
                    EventType.VOICE_CREATED,
                    {"voice_id": str(voice_id)}
                )
                continue
            
            # 실패 확인
            if voice_details.get("status") == "failed":
                await voice_repo.update(
                    voice_id=voice_id,
                    status="failed",
                )
                continue
            
            # 아직 처리 중이면 재시도
            if attempts < job["max_attempts"]:
                job["attempts"] += 1
                await sync_queue.enqueue(
                    voice_id=job["voice_id"],
                    elevenlabs_voice_id=elevenlabs_voice_id,
                )
            else:
                # 최대 시도 횟수 초과
                await voice_repo.update(
                    voice_id=voice_id,
                    status="failed",
                )
                
        except Exception as e:
            logger.error(f"Voice sync error: {e}")
            # 에러 발생 시 재시도
            if attempts < job["max_attempts"]:
                job["attempts"] += 1
                await sync_queue.enqueue(
                    voice_id=job["voice_id"],
                    elevenlabs_voice_id=elevenlabs_voice_id,
                )
```

---

### Option 3: Scheduled Task (주기적 배치) ⭐⭐⭐⭐

#### 구현 방식
- 주기적으로 (예: 1분마다) 모든 "processing" 상태 Voice 조회
- 각 Voice의 상태 확인 및 업데이트

#### 장점 ✅
- 구현 간단
- 서버 재시작 시에도 작업 유지
- 확장 가능 (여러 인스턴스 실행 가능)

#### 단점 ❌
- 주기적 실행으로 인한 지연
- 불필요한 API 호출 가능

#### 구현 예시
```python
# 1. Scheduled Task (main.py lifespan에 추가)
async def sync_voice_status_periodically():
    """주기적으로 Voice 상태 동기화"""
    while True:
        try:
            await asyncio.sleep(60)  # 1분마다 실행
            
            # "processing" 상태인 모든 Voice 조회
            voice_repo = VoiceRepository(db_session)
            processing_voices = await voice_repo.get_by_status("processing")
            
            tts_provider = AIProviderFactory().get_tts_provider()
            
            for voice in processing_voices:
                try:
                    # ElevenLabs API에서 Voice 상세 정보 조회
                    voice_details = await tts_provider.get_voice_details(
                        voice.elevenlabs_voice_id
                    )
                    
                    # 완료 확인
                    if voice_details.get("status") == "completed":
                        await voice_repo.update(
                            voice_id=voice.id,
                            preview_url=voice_details.get("preview_url"),
                            status="completed",
                        )
                        
                        # 이벤트 발행
                        await event_bus.publish(
                            EventType.VOICE_CREATED,
                            {"voice_id": str(voice.id), "user_id": str(voice.user_id)}
                        )
                    
                    # 실패 확인
                    elif voice_details.get("status") == "failed":
                        await voice_repo.update(
                            voice_id=voice.id,
                            status="failed",
                        )
                        
                except Exception as e:
                    logger.error(f"Voice sync error for {voice.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Voice sync task error: {e}")
            await asyncio.sleep(60)

# 2. lifespan에서 시작
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 기존 코드 ...
    
    # Voice 동기화 작업 시작
    sync_task = asyncio.create_task(sync_voice_status_periodically())
    
    yield
    
    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
```

---

### Option 4: Webhook (현재 미지원) ❌

#### ⚠️ 확인 결과
**ElevenLabs는 웹훅을 지원하지만, Voice Clone 생성 완료 웹훅은 제공하지 않습니다.**

#### 지원되는 웹훅 이벤트
- `post_call_transcription`: 에이전트 플랫폼 통화 완료
- `voice_removal_notice`: 공유된 보이스 제거 예정
- `voice_removal_notice_withdrawn`: 공유된 보이스 제거 예정 철회
- `voice_removed`: 공유된 보이스 제거 완료

#### 결론
- **Voice Clone 생성 완료 웹훅은 없음**
- 폴링 방식(Scheduled Task 또는 Redis Queue) 사용 필요
- 향후 ElevenLabs가 지원할 경우 전환 고려

#### 구현 예시 (가정)
```python
@router.post("/webhooks/elevenlabs/voice-completed")
async def elevenlabs_voice_webhook(
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    """ElevenLabs Voice 완료 웹훅"""
    # 서명 검증 (보안)
    # ...
    
    voice_id = request.get("voice_id")
    status = request.get("status")
    preview_url = request.get("preview_url")
    
    if status == "completed":
        # DB에서 해당 Voice 조회 (elevenlabs_voice_id로)
        voice_repo = VoiceRepository(db)
        voice = await voice_repo.get_by_elevenlabs_id(voice_id)
        
        if voice:
            await voice_repo.update(
                voice_id=voice.id,
                preview_url=preview_url,
                status="completed",
            )
            
            # 이벤트 발행
            await event_bus.publish(
                EventType.VOICE_CREATED,
                {"voice_id": str(voice.id), "user_id": str(voice.user_id)}
            )
    
    return {"status": "ok"}
```

---

## 📊 비교표

| 항목 | Option 1: BackgroundTasks | Option 2: Redis Queue | Option 3: Scheduled Task | Option 4: Webhook |
|------|--------------------------|----------------------|-------------------------|------------------|
| **구현 복잡도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **확장성** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **실시간성** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **안정성** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **API 호출 효율** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **서버 재시작 대응** | ❌ | ✅ | ✅ | ✅ |

---

## 🎯 최종 권장사항

### 단기: Option 3 (Scheduled Task) ⭐⭐⭐⭐

#### 이유
- 구현 간단
- 서버 재시작 시에도 작업 유지
- 확장 가능
- 현재 인프라 활용 (Redis, Event Bus)

#### 구현 단계
1. Voice 모델에 `status` 필드 추가
2. Scheduled Task 구현
3. `get_voice_details` API 메서드 추가
4. 테스트

### 장기: Option 2 (Redis Queue) 또는 Option 4 (Webhook)

#### Option 2로 전환 시점
- Voice 생성량이 많아질 때
- 더 정밀한 제어가 필요할 때

#### Option 4로 전환 시점
- ElevenLabs가 웹훅을 지원할 때
- 실시간 처리가 중요할 때

---

## 📝 구현 계획 (Option 3 기준)

### Phase 1: DB 모델 수정

```python
class Voice(Base):
    # ... 기존 필드 ...
    status: Mapped[str] = mapped_column(
        String(20),
        default="processing",  # processing, completed, failed
        index=True
    )
    preview_url: Mapped[Optional[str]] = mapped_column(String(1024))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
```

### Phase 2: ElevenLabs Provider에 메서드 추가

```python
async def get_voice_details(self, voice_id: str) -> Dict[str, Any]:
    """Voice 상세 정보 조회 (상태 포함)"""
    # GET /v1/voices/{voice_id}
    # 응답에 status, preview_url 등 포함
```

### Phase 3: Scheduled Task 구현

```python
async def sync_voice_status_periodically():
    """주기적으로 Voice 상태 동기화"""
    # 구현 (위 예시 참고)
```

### Phase 4: Voice 생성 로직 수정

```python
async def create_voice_clone(...):
    # status="processing"으로 저장
    # Scheduled Task가 자동으로 처리
```

---

## 🔄 하이브리드 접근 (권장)

### 초기: Scheduled Task
- 빠른 구현
- 안정적 동작

### 확장: Redis Queue 추가
- 더 정밀한 제어
- 우선순위 큐
- 재시도 로직

### 최적: Webhook 추가 (현재 불가능)
- **ElevenLabs가 Voice Clone 완료 웹훅을 지원하지 않음**
- 향후 지원 시 전환 고려

---

## ✅ 체크리스트

### Option 3 구현
- [ ] Voice 모델에 `status`, `preview_url`, `completed_at` 필드 추가
- [ ] 마이그레이션 작성
- [ ] `ElevenLabsTTSProvider.get_voice_details()` 구현
- [ ] `sync_voice_status_periodically()` 함수 구현
- [ ] `lifespan`에 Scheduled Task 추가
- [ ] `create_voice_clone()` 수정 (status="processing")
- [ ] 테스트 작성

---

## 📚 참고 자료

- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Redis Queue 패턴
- ElevenLabs API 문서: https://elevenlabs.io/docs/api-reference
- ElevenLabs 웹훅 문서: https://elevenlabs.io/docs/product-guides/administration/webhooks
  - **참고**: Voice Clone 완료 웹훅은 지원하지 않음

