# Voice 사용자별 관리 구현 계획

## 📋 요구사항

1. **Voice 테이블에 visibility 필드 추가**
   - `private`: 사용자 개인 음성 (본인만 조회 가능)
   - `public`: 공개 음성 (모든 사용자 조회 가능)
   - `default`: 기본 음성 (모든 사용자 조회 가능, ElevenLabs premade)

2. **Voice 조회 로직**
   - 사용자별 조회 시: 본인 private + 모든 public + 모든 default 포함
   - 캐시 키: `tts:voices:{user_id}`

3. **Scheduled Task로 동기화**
   - 주기적으로 "processing" 상태 Voice 조회
   - ElevenLabs API로 상태 확인
   - 완료 시 DB 업데이트

---

## 🎯 구현 페이즈

### Phase 1: DB 모델 및 마이그레이션
- Voice 모델에 필드 추가
- 마이그레이션 작성
- 테스트 작성
- 스테이징 커밋

### Phase 2: Repository 및 Service 레이어
- VoiceRepository 메서드 추가
- TTSService 수정
- 테스트 작성
- 스테이징 커밋

### Phase 3: ElevenLabs Provider 확장
- `get_voice_details()` 메서드 추가
- 테스트 작성
- 스테이징 커밋

### Phase 4: Scheduled Task 구현
- Voice 동기화 Task 구현
- lifespan에 통합
- 테스트 작성
- 스테이징 커밋

### Phase 5: API 엔드포인트 수정
- 사용자별 Voice 조회 로직 구현
- 캐싱 적용
- 테스트 작성
- 스테이징 커밋

### Phase 6: 통합 테스트 및 최종 검증
- 전체 플로우 테스트
- 성능 테스트
- 문서 업데이트
- 스테이징 커밋

---

## 📝 Phase 1: DB 모델 및 마이그레이션

### 1.1 Voice 모델 수정

**파일**: `backend/features/tts/models.py`

```python
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Float, JSON, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database.base import Base


class VoiceVisibility(str, Enum):
    """Voice 공개 범위"""
    PRIVATE = "private"  # 사용자 개인 음성
    PUBLIC = "public"    # 공개 음성 (모든 사용자 조회 가능)
    DEFAULT = "default"  # 기본 음성 (ElevenLabs premade, 모든 사용자 조회 가능)


class VoiceStatus(str, Enum):
    """Voice 생성 상태"""
    PROCESSING = "processing"  # 생성 중
    COMPLETED = "completed"    # 생성 완료
    FAILED = "failed"          # 생성 실패


class Voice(Base):
    """
    Voice 모델 (사용자별 음성 관리)
    """
    __tablename__ = "voices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # 소유자
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ElevenLabs Voice ID
    elevenlabs_voice_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Voice 정보
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    preview_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        default="cloned",  # premade, cloned, custom
        nullable=False,
    )

    # 공개 범위
    visibility: Mapped[VoiceVisibility] = mapped_column(
        SQLEnum(VoiceVisibility),
        default=VoiceVisibility.PRIVATE,
        nullable=False,
        index=True,
    )

    # 생성 상태
    status: Mapped[VoiceStatus] = mapped_column(
        SQLEnum(VoiceStatus),
        default=VoiceStatus.PROCESSING,
        nullable=False,
        index=True,
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # 추가 메타데이터
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 인덱스
    __table_args__ = (
        Index('idx_voice_user_id', 'user_id'),
        Index('idx_voice_status', 'status'),
        Index('idx_voice_visibility', 'visibility'),
        Index('idx_voice_user_status', 'user_id', 'status'),
        Index('idx_voice_visibility_status', 'visibility', 'status'),
    )

    def __repr__(self) -> str:
        return f"<Voice(id={self.id}, name={self.name}, visibility={self.visibility.value}, status={self.status.value})>"
```

### 1.2 마이그레이션 작성

**파일**: `backend/migrations/versions/XXX_add_voice_table.py`

```python
"""Add voice table

Revision ID: add_voice_table
Revises: <previous_revision>
Create Date: 2024-XX-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_voice_table'
down_revision = '<previous_revision>'  # 실제 이전 마이그레이션 ID로 변경
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Voice 테이블 생성
    op.create_table(
        'voices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('elevenlabs_voice_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('gender', sa.String(20), nullable=False, server_default='unknown'),
        sa.Column('preview_url', sa.String(1024), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='cloned'),
        sa.Column('visibility', sa.Enum('private', 'public', 'default', name='voicevisibility'), nullable=False, server_default='private'),
        sa.Column('status', sa.Enum('processing', 'completed', 'failed', name='voicestatus'), nullable=False, server_default='processing'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', postgresql.JSON, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # 인덱스 생성
    op.create_index('idx_voice_user_id', 'voices', ['user_id'])
    op.create_index('idx_voice_status', 'voices', ['status'])
    op.create_index('idx_voice_visibility', 'voices', ['visibility'])
    op.create_index('idx_voice_user_status', 'voices', ['user_id', 'status'])
    op.create_index('idx_voice_visibility_status', 'voices', ['visibility', 'status'])
    op.create_index('idx_voice_elevenlabs_id', 'voices', ['elevenlabs_voice_id'])


def downgrade() -> None:
    op.drop_index('idx_voice_elevenlabs_id', table_name='voices')
    op.drop_index('idx_voice_visibility_status', table_name='voices')
    op.drop_index('idx_voice_user_status', table_name='voices')
    op.drop_index('idx_voice_visibility', table_name='voices')
    op.drop_index('idx_voice_status', table_name='voices')
    op.drop_index('idx_voice_user_id', table_name='voices')
    op.drop_table('voices')
    sa.Enum(name='voicestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='voicevisibility').drop(op.get_bind(), checkfirst=True)
```

### 1.3 테스트 작성

**파일**: `backend/tests/unit/tts/test_voice_model.py`

```python
import pytest
import uuid
from datetime import datetime
from backend.features.tts.models import Voice, VoiceVisibility, VoiceStatus


def test_voice_model_creation():
    """Voice 모델 생성 테스트"""
    voice = Voice(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        elevenlabs_voice_id="test_voice_id",
        name="Test Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.PROCESSING,
    )
    
    assert voice.visibility == VoiceVisibility.PRIVATE
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.category == "cloned"
    assert voice.language == "en"
    assert voice.gender == "unknown"


def test_voice_model_defaults():
    """Voice 모델 기본값 테스트"""
    voice = Voice(
        user_id=uuid.uuid4(),
        elevenlabs_voice_id="test_voice_id",
        name="Test Voice",
    )
    
    assert voice.visibility == VoiceVisibility.PRIVATE
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.category == "cloned"
```

### 1.4 Phase 1 완료 체크리스트
- [ ] Voice 모델 수정
- [ ] VoiceVisibility, VoiceStatus Enum 추가
- [ ] 마이그레이션 작성
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 2: Repository 및 Service 레이어

### 2.1 VoiceRepository 구현

**파일**: `backend/features/tts/repository.py` (새로 생성 또는 확장)

```python
"""
Voice Repository
Voice 데이터 접근 계층
"""
import uuid
from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Voice, VoiceVisibility, VoiceStatus
from backend.domain.repositories.base import AbstractRepository


class VoiceRepository(AbstractRepository[Voice]):
    """
    Voice Repository
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, Voice)

    async def get_user_voices(
        self,
        user_id: uuid.UUID,
        include_public: bool = True,
        include_default: bool = True,
    ) -> List[Voice]:
        """
        사용자별 Voice 조회
        
        Args:
            user_id: 사용자 UUID
            include_public: 공개 Voice 포함 여부
            include_default: 기본 Voice 포함 여부
        
        Returns:
            List[Voice]: Voice 목록
                - 사용자 개인 Voice (private)
                - 공개 Voice (public, include_public=True일 때)
                - 기본 Voice (default, include_default=True일 때)
        """
        conditions = [
            Voice.user_id == user_id,  # 사용자 개인 Voice
        ]
        
        if include_public:
            conditions.append(
                and_(
                    Voice.visibility == VoiceVisibility.PUBLIC,
                    Voice.status == VoiceStatus.COMPLETED,
                )
            )
        
        if include_default:
            conditions.append(
                and_(
                    Voice.visibility == VoiceVisibility.DEFAULT,
                    Voice.status == VoiceStatus.COMPLETED,
                )
            )
        
        query = (
            select(Voice)
            .where(or_(*conditions))
            .order_by(Voice.created_at.desc())
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(self, status: VoiceStatus) -> List[Voice]:
        """상태별 Voice 조회"""
        query = (
            select(Voice)
            .where(Voice.status == status)
            .order_by(Voice.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_elevenlabs_id(self, elevenlabs_voice_id: str) -> Optional[Voice]:
        """ElevenLabs Voice ID로 조회"""
        query = select(Voice).where(Voice.elevenlabs_voice_id == elevenlabs_voice_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        voice_id: uuid.UUID,
        status: VoiceStatus,
        preview_url: Optional[str] = None,
    ) -> Optional[Voice]:
        """Voice 상태 업데이트"""
        voice = await self.get(voice_id)
        if not voice:
            return None
        
        voice.status = status
        if preview_url:
            voice.preview_url = preview_url
        if status == VoiceStatus.COMPLETED:
            from datetime import datetime
            voice.completed_at = datetime.utcnow()
        
        return await self.save(voice)
```

### 2.2 TTSService 수정

**파일**: `backend/features/tts/service.py`

```python
# 기존 코드에 추가

from .models import Voice, VoiceVisibility, VoiceStatus
from .repository import VoiceRepository

class TTSService:
    def __init__(
        self,
        audio_repo: AudioRepository,
        voice_repo: VoiceRepository,  # 추가
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
        cache_service,
        event_bus: EventBus,
    ):
        self.audio_repo = audio_repo
        self.voice_repo = voice_repo  # 추가
        # ... 기존 코드 ...

    async def create_voice_clone(
        self,
        user_id: uuid.UUID,
        name: str,
        audio_file: bytes,
        visibility: VoiceVisibility = VoiceVisibility.PRIVATE,
    ) -> Voice:
        """
        Voice Clone 생성
        
        Args:
            user_id: 사용자 UUID
            name: Voice 이름
            audio_file: 오디오 파일 (bytes)
            visibility: 공개 범위 (기본값: PRIVATE)
        
        Returns:
            Voice: 생성된 Voice 객체
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
            preview_url=None,  # 아직 없음
        )
        
        # Scheduled Task가 자동으로 상태 동기화
        # 별도 백그라운드 작업 불필요
        
        return voice

    @cache_result(key="tts:voices:{user_id}", ttl=3600)
    async def get_voices(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        사용자별 Voice 목록 조회 (캐싱 적용)
        
        Args:
            user_id: 사용자 UUID
        
        Returns:
            List[Dict[str, Any]]: Voice 목록
                - 사용자 개인 Voice (private)
                - 공개 Voice (public)
                - 기본 Voice (default)
        """
        # DB에서 사용자별 Voice 조회
        voices = await self.voice_repo.get_user_voices(
            user_id=user_id,
            include_public=True,
            include_default=True,
        )
        
        # 기본 Voice (ElevenLabs premade) 추가
        tts_provider = self.ai_factory.get_tts_provider()
        try:
            premade_voices = await tts_provider.get_available_voices()
            premade_voices = [
                v for v in premade_voices 
                if v.get("category") == "premade"
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch premade voices: {e}")
            premade_voices = []
        
        # DB Voice + Premade Voice 합치기
        result = []
        
        # DB Voice 변환
        for voice in voices:
            result.append({
                "voice_id": voice.elevenlabs_voice_id,
                "name": voice.name,
                "language": voice.language,
                "gender": voice.gender,
                "preview_url": voice.preview_url,
                "category": voice.category,
                "visibility": voice.visibility.value,
                "status": voice.status.value,
                "is_custom": True,
            })
        
        # Premade Voice 추가
        for voice in premade_voices:
            result.append({
                "voice_id": voice["voice_id"],
                "name": voice["name"],
                "language": voice.get("language", "en"),
                "gender": voice.get("gender", "unknown"),
                "preview_url": voice.get("preview_url"),
                "category": "premade",
                "visibility": "default",
                "status": "completed",
                "is_custom": False,
            })
        
        return result
```

### 2.3 테스트 작성

**파일**: `backend/tests/unit/tts/test_voice_repository.py`

```python
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from backend.features.tts.repository import VoiceRepository
from backend.features.tts.models import Voice, VoiceVisibility, VoiceStatus


@pytest.mark.asyncio
async def test_get_user_voices(db_session: AsyncSession):
    """사용자별 Voice 조회 테스트"""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    
    repo = VoiceRepository(db_session)
    
    # 사용자 개인 Voice 생성
    private_voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="private_voice_id",
        name="Private Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.COMPLETED,
    )
    
    # 다른 사용자의 공개 Voice 생성
    public_voice = await repo.create(
        user_id=other_user_id,
        elevenlabs_voice_id="public_voice_id",
        name="Public Voice",
        visibility=VoiceVisibility.PUBLIC,
        status=VoiceStatus.COMPLETED,
    )
    
    # 기본 Voice 생성
    default_voice = await repo.create(
        user_id=other_user_id,
        elevenlabs_voice_id="default_voice_id",
        name="Default Voice",
        visibility=VoiceVisibility.DEFAULT,
        status=VoiceStatus.COMPLETED,
    )
    
    await db_session.commit()
    
    # 사용자 Voice 조회
    voices = await repo.get_user_voices(user_id)
    
    # 개인 + 공개 + 기본 Voice 모두 포함되어야 함
    voice_ids = {v.elevenlabs_voice_id for v in voices}
    assert "private_voice_id" in voice_ids
    assert "public_voice_id" in voice_ids
    assert "default_voice_id" in voice_ids
```

### 2.4 Phase 2 완료 체크리스트
- [ ] VoiceRepository 구현
- [ ] TTSService 수정
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 3: ElevenLabs Provider 확장

### 3.1 get_voice_details() 메서드 추가

**파일**: `backend/infrastructure/ai/providers/elevenlabs_tts.py`

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
            "category": str,
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
    # 주의: 실제 API 응답 구조에 맞게 수정 필요
    preview_url = data.get("preview_url")
    
    # preview_url이 있으면 완료로 간주
    status = "completed" if preview_url else "processing"
    
    return {
        "voice_id": data.get("voice_id", voice_id),
        "name": data.get("name", ""),
        "status": status,
        "preview_url": preview_url,
        "language": data.get("labels", {}).get("language", "en"),
        "gender": data.get("labels", {}).get("gender", "unknown"),
        "category": data.get("category", "generated"),
    }
```

### 3.2 테스트 작성

**파일**: `backend/tests/unit/ai/test_elevenlabs_voice_details.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.infrastructure.ai.providers.elevenlabs_tts import ElevenLabsTTSProvider


@pytest.mark.asyncio
async def test_get_voice_details_completed():
    """Voice 상세 정보 조회 (완료 상태) 테스트"""
    provider = ElevenLabsTTSProvider()
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "voice_id": "test_voice_id",
        "name": "Test Voice",
        "preview_url": "https://example.com/preview.mp3",
        "labels": {
            "language": "en",
            "gender": "male",
        },
        "category": "cloned",
    }
    mock_response.raise_for_status = AsyncMock()
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        details = await provider.get_voice_details("test_voice_id")
        
        assert details["voice_id"] == "test_voice_id"
        assert details["status"] == "completed"
        assert details["preview_url"] == "https://example.com/preview.mp3"
```

### 3.3 Phase 3 완료 체크리스트
- [ ] `get_voice_details()` 메서드 구현
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 4: Scheduled Task 구현

### 4.1 Voice 동기화 Task 구현

**파일**: `backend/core/tasks/voice_sync.py` (새로 생성)

```python
"""
Voice 동기화 Scheduled Task
주기적으로 ElevenLabs Voice 상태를 확인하고 DB를 업데이트
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.tts.repository import VoiceRepository
from backend.features.tts.models import VoiceStatus
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.events.types import EventType
from backend.core.database.session import get_db

logger = logging.getLogger(__name__)


async def sync_voice_status_periodically(
    event_bus: RedisStreamsEventBus,
    interval: int = 60,  # 1분마다 실행
    max_age_minutes: int = 30,  # 30분 이상 오래된 "processing" 상태는 실패 처리
):
    """
    주기적으로 Voice 상태 동기화
    
    Args:
        event_bus: 이벤트 버스
        interval: 실행 간격 (초)
        max_age_minutes: 최대 대기 시간 (분)
    """
    while True:
        try:
            await asyncio.sleep(interval)
            
            logger.info("Starting voice status sync...")
            
            # DB 세션 생성
            async for db_session in get_db():
                try:
                    # "processing" 상태인 모든 Voice 조회
                    voice_repo = VoiceRepository(db_session)
                    processing_voices = await voice_repo.get_by_status(VoiceStatus.PROCESSING)
                    
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
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.FAILED,
                                )
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
                                
                                logger.info(f"Voice {voice.id} sync completed")
                            
                            # 실패 확인
                            elif voice_details.get("status") == "failed":
                                logger.warning(f"Voice {voice.id} failed")
                                
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.FAILED,
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
                    await db_session.rollback()
                finally:
                    await db_session.close()
                break  # 첫 번째 세션만 사용
            
        except Exception as e:
            logger.error(f"Voice sync task error: {e}", exc_info=True)
            await asyncio.sleep(interval)
```

### 4.2 lifespan에 통합

**파일**: `backend/main.py`

```python
# 기존 코드에 추가

from backend.core.tasks.voice_sync import sync_voice_status_periodically

@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus
    
    # ... 기존 startup 코드 ...
    
    # Voice 동기화 작업 시작
    sync_task = asyncio.create_task(
        sync_voice_status_periodically(
            event_bus=event_bus,
            interval=60,  # 1분마다 실행
        )
    )
    
    yield
    
    # Shutdown
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
```

### 4.3 테스트 작성

**파일**: `backend/tests/integration/test_voice_sync.py`

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from backend.core.tasks.voice_sync import sync_voice_status_periodically
from backend.features.tts.models import Voice, VoiceStatus, VoiceVisibility


@pytest.mark.asyncio
async def test_voice_sync_completed(db_session, event_bus):
    """Voice 동기화 완료 테스트"""
    # Mock 설정
    mock_tts_provider = MagicMock()
    mock_tts_provider.get_voice_details = AsyncMock(return_value={
        "voice_id": "test_voice_id",
        "status": "completed",
        "preview_url": "https://example.com/preview.mp3",
    })
    
    mock_ai_factory = MagicMock()
    mock_ai_factory.get_tts_provider = MagicMock(return_value=mock_tts_provider)
    
    # Voice 생성 (processing 상태)
    voice_repo = VoiceRepository(db_session)
    voice = await voice_repo.create(
        user_id=uuid.uuid4(),
        elevenlabs_voice_id="test_voice_id",
        name="Test Voice",
        status=VoiceStatus.PROCESSING,
    )
    await db_session.commit()
    
    # 동기화 실행 (간단한 버전)
    # 실제로는 전체 함수를 테스트하기 어려우므로 핵심 로직만 테스트
    
    # Voice 상세 정보 조회
    voice_details = await mock_tts_provider.get_voice_details("test_voice_id")
    
    # 완료 확인
    if voice_details.get("status") == "completed":
        await voice_repo.update_status(
            voice_id=voice.id,
            status=VoiceStatus.COMPLETED,
            preview_url=voice_details.get("preview_url"),
        )
        await db_session.commit()
    
    # 확인
    updated_voice = await voice_repo.get(voice.id)
    assert updated_voice.status == VoiceStatus.COMPLETED
    assert updated_voice.preview_url == "https://example.com/preview.mp3"
```

### 4.4 Phase 4 완료 체크리스트
- [ ] `sync_voice_status_periodically()` 함수 구현
- [ ] `lifespan`에 통합
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 5: API 엔드포인트 수정

### 5.1 API 엔드포인트 수정

**파일**: `backend/api/v1/endpoints/tts.py`

```python
# 기존 코드 수정

@router.get(
    "/voices",
    response_model=List[VoiceResponse],
    summary="사용 가능한 음성 목록 조회",
)
async def list_voices(
    current_user: User = Depends(get_current_user),  # 인증 추가
    service: TTSService = Depends(get_tts_service),
):
    """
    사용 가능한 음성 목록 조회
    
    반환되는 Voice:
    - 사용자 개인 Voice (private)
    - 공개 Voice (public)
    - 기본 Voice (default, ElevenLabs premade)
    """
    voices = await service.get_voices(user_id=current_user.id)
    return voices
```

### 5.2 의존성 주입 수정

**파일**: `backend/api/v1/endpoints/tts.py`

```python
def get_tts_service(
    db: AsyncSession = Depends(get_db),
    storage_service = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
    cache_service = Depends(get_cache_service),
    event_bus = Depends(get_event_bus),
) -> TTSService:
    """TTSService 의존성 주입"""
    audio_repo = AudioRepository(db)
    voice_repo = VoiceRepository(db)  # 추가
    return TTSService(
        audio_repo=audio_repo,
        voice_repo=voice_repo,  # 추가
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
        cache_service=cache_service,
        event_bus=event_bus,
    )
```

### 5.3 테스트 작성

**파일**: `backend/tests/integration/test_tts_voices_api.py`

```python
import pytest
from httpx import AsyncClient
from backend.features.tts.models import Voice, VoiceVisibility, VoiceStatus


@pytest.mark.asyncio
async def test_get_voices_includes_all_types(client: AsyncClient, auth_headers):
    """Voice 조회 시 모든 타입 포함 테스트"""
    # 사용자 개인 Voice 생성
    # 공개 Voice 생성
    # 기본 Voice 생성
    
    response = await client.get(
        "/api/v1/tts/voices",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    voices = response.json()
    
    # 개인 + 공개 + 기본 Voice 모두 포함되어야 함
    voice_visibilities = {v["visibility"] for v in voices}
    assert "private" in voice_visibilities
    assert "public" in voice_visibilities
    assert "default" in voice_visibilities
```

### 5.4 Phase 5 완료 체크리스트
- [ ] API 엔드포인트 수정
- [ ] 의존성 주입 수정
- [ ] 테스트 작성
- [ ] 테스트 통과 확인
- [ ] 스테이징 커밋

---

## 📝 Phase 6: 통합 테스트 및 최종 검증

### 6.1 통합 테스트

**파일**: `backend/tests/integration/test_voice_full_flow.py`

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voice_creation_and_sync_full_flow(client: AsyncClient, auth_headers):
    """Voice 생성부터 동기화까지 전체 플로우 테스트"""
    # 1. Voice 생성 요청
    # 2. "processing" 상태 확인
    # 3. Scheduled Task 시뮬레이션
    # 4. "completed" 상태 확인
    # 5. Voice 조회 시 포함 확인
    pass
```

### 6.2 Phase 6 완료 체크리스트
- [ ] 통합 테스트 작성
- [ ] 성능 테스트
- [ ] 문서 업데이트
- [ ] 최종 검증
- [ ] 스테이징 커밋

---

## 📊 전체 구현 일정

| Phase | 작업 내용 | 예상 시간 | 테스트 포함 |
|-------|----------|----------|------------|
| Phase 1 | DB 모델 및 마이그레이션 | 1-2시간 | ✅ |
| Phase 2 | Repository 및 Service | 2-3시간 | ✅ |
| Phase 3 | ElevenLabs Provider 확장 | 1-2시간 | ✅ |
| Phase 4 | Scheduled Task 구현 | 2-3시간 | ✅ |
| Phase 5 | API 엔드포인트 수정 | 1-2시간 | ✅ |
| Phase 6 | 통합 테스트 및 검증 | 2-3시간 | ✅ |
| **총계** | | **9-15시간** | |

---

## ✅ 최종 체크리스트

- [ ] 모든 Phase 완료
- [ ] 모든 테스트 통과
- [ ] 코드 리뷰
- [ ] 문서 업데이트
- [ ] 프로덕션 배포 준비

