"""
Voice 동기화 Scheduled Task (Redis 최적화)
Redis 큐에 등록된 작업만 처리
"""
import asyncio
import logging
import uuid
from datetime import datetime
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
            
        except asyncio.CancelledError:
            logger.info("Voice sync task cancelled")
            await voice_queue.close()
            raise
        except Exception as e:
            logger.error(f"Voice sync task error: {e}", exc_info=True)
            await asyncio.sleep(interval)

