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
from backend.core.utils.trace import log_process

from backend.core.logging import get_logger

logger = get_logger(__name__)


@log_process(step="Task Voice Sync", desc="Voice Cloning 상태 동기화 작업")
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
            
            logger.debug("Voice sync heartbeat", extra={"queued_count": len(queued_voice_ids)})

            if not queued_voice_ids:
                # logger.debug("No voices in sync queue, skipping") # 너무 빈번하면 시끄러우므로 debug 유지
                continue
            
            logger.info(f"Found {len(queued_voice_ids)} voices in sync queue", extra={"voice_ids": list(queued_voice_ids)})
            
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
                            age_minutes = (datetime.now() - voice.created_at).total_seconds() / 60
                            if age_minutes > max_age_minutes:
                                logger.warning(
                                    f"Voice {voice.id} exceeded max age ({age_minutes:.1f} minutes), "
                                    f"marking as failed"
                                )
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.FAILED,
                                )
                                
                                # 이벤트 발행 (캐시 무효화)
                                await event_bus.publish(
                                    EventType.VOICE_UPDATED,
                                    {
                                        "voice_id": str(voice.id),
                                        "user_id": str(voice.user_id),
                                    }
                                )
                                # 큐에서 제거
                                await voice_queue.dequeue(voice.id)
                                continue
                            
                            # ElevenLabs API에서 Voice 상세 정보 조회
                            voice_details = await tts_provider.get_voice_details(
                                voice.elevenlabs_voice_id
                            )
                            
                            preview_url = voice_details.get("preview_url")
                            
                            # 1. Preview URL이 있는 경우 -> 성공
                            if preview_url:
                                logger.info(f"Voice {voice.id} completed with preview url")
                                await voice_repo.update_status(
                                    voice_id=voice.id,
                                    status=VoiceStatus.COMPLETED,
                                    preview_url=preview_url,
                                )
                                # 완료 이벤트 및 큐 제거
                                await event_bus.publish(
                                    EventType.VOICE_CREATED,
                                    {"voice_id": str(voice.id), "user_id": str(voice.user_id)}
                                )
                                await voice_queue.dequeue(voice.id)
                                continue

                            # 2. Preview URL이 없는 경우 -> 추가 검증 필요
                            
                            # 이미 Trigger TTS를 성공했는지 확인
                            is_triggered = await voice_queue.is_trigger_processed(voice.id)
                            
                            if is_triggered:
                                # 이미 Trigger 성공했으나 아직 URL 없음
                                if age_minutes > max_age_minutes:
                                    # 30분 지남 -> 성공 처리 (Case: TTS 작동하지만 URL만 없는 경우)
                                    logger.info(
                                        f"Voice {voice.id} time expired but TTS triggered successfully. "
                                        f"Marking as COMPLETED without preview URL"
                                    )
                                    await voice_repo.update_status(
                                        voice_id=voice.id,
                                        status=VoiceStatus.COMPLETED,
                                        preview_url=None, # URL 없이 완료
                                    )
                                    await event_bus.publish(
                                        EventType.VOICE_CREATED,
                                        {"voice_id": str(voice.id), "user_id": str(voice.user_id)}
                                    )
                                    await voice_queue.dequeue(voice.id)
                                else:
                                    # 아직 30분 안됨 -> 계속 대기 (URL 생성 기다림)
                                    logger.debug(f"Voice {voice.id} triggered but waiting for URL (age: {age_minutes:.1f}m)")
                            
                            else:
                                # Trigger 시도 안함 (또는 실패 상태)
                                try:
                                    logger.info(f"Voice {voice.id} missing preview, attempting trigger TTS")
                                    # 짧은 텍스트로 TTS 요청 (결과 무시)
                                    await tts_provider.text_to_speech(
                                        text="Hello",
                                        voice_id=voice.elevenlabs_voice_id
                                    )
                                    # 성공 시 플래그 설정
                                    await voice_queue.mark_trigger_processed(voice.id)
                                    logger.info(f"Trigger TTS successful for voice {voice.id}")
                                    
                                    # 이번 턴은 대기 (다음 턴에 URL 확인 or 시간 체크)
                                    
                                except Exception as trigger_error:
                                    logger.warning(
                                        f"Trigger TTS failed for voice {voice.id}: {trigger_error}"
                                    )
                                    # 실패 시 플래그 설정 안함 -> 다음 턴에 재시도
                                    
                                    if age_minutes > max_age_minutes:
                                        # 30분 지났는데도 Trigger 실패 -> 진짜 실패
                                        logger.warning(f"Voice {voice.id} failed (timeout & tts failed)")
                                        await voice_repo.update_status(
                                            voice_id=voice.id,
                                            status=VoiceStatus.FAILED,
                                        )
                                        await event_bus.publish(
                                            EventType.VOICE_UPDATED,
                                            {"voice_id": str(voice.id), "user_id": str(voice.user_id)}
                                        )
                                        await voice_queue.dequeue(voice.id)
                        
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

