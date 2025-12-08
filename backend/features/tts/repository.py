"""
Audio Repository
TTS 오디오 및 Voice 데이터 접근 계층
"""
import uuid
from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Audio, Voice, VoiceVisibility, VoiceStatus
from backend.domain.repositories.base import AbstractRepository


class AudioRepository(AbstractRepository[Audio]):
    """
    오디오 레포지토리
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session, Audio)


class VoiceRepository(AbstractRepository[Voice]):
    """
    Voice Repository
    
    Voice 데이터 접근 계층
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Voice)
    
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
        """
        상태별 Voice 조회
        
        Args:
            status: Voice 상태
        
        Returns:
            List[Voice]: 상태별 Voice 목록
        """
        query = (
            select(Voice)
            .where(Voice.status == status)
            .order_by(Voice.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_elevenlabs_id(self, elevenlabs_voice_id: str) -> Optional[Voice]:
        """
        ElevenLabs Voice ID로 조회
        
        Args:
            elevenlabs_voice_id: ElevenLabs Voice ID
        
        Returns:
            Optional[Voice]: Voice 객체 또는 None
        """
        query = select(Voice).where(Voice.elevenlabs_voice_id == elevenlabs_voice_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        voice_id: uuid.UUID,
        status: VoiceStatus,
        preview_url: Optional[str] = None,
    ) -> Optional[Voice]:
        """
        Voice 상태 업데이트
        
        Args:
            voice_id: Voice UUID
            status: 새로운 상태
            preview_url: Preview URL (완료 시)
        
        Returns:
            Optional[Voice]: 업데이트된 Voice 객체 또는 None
        """
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
    
    async def save(self, instance: Voice) -> Voice:
        """
        Voice 저장 (AbstractRepository의 save 오버라이드)
        
        Args:
            instance: Voice 인스턴스
        
        Returns:
            Voice: 저장된 Voice 객체
        """
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
