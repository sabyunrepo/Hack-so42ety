import asyncio
import json
import logging
import uuid
import os
import aiofiles
from typing import Set, Optional
import redis.asyncio as aioredis
from sqlalchemy import select

from backend.core.config import settings
from backend.core.events.types import EventType
from backend.core.database.session import AsyncSessionLocal
from backend.features.storybook.models import DialogueAudio
from backend.infrastructure.ai.factory import AIProviderFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSWorker:
    """
    TTS Worker (Consumer)
    Redis Streams에서 작업을 가져와 ElevenLabs TTS를 생성하고 파일로 저장합니다.
    Semaphore(3)을 사용하여 동시 요청 수를 제한합니다 (총 5개 중 2개는 실시간 Word TTS용으로 확보).
    """

    def __init__(self):
        self.redis_url = settings.redis_url
        self.stream_name = f"events:{EventType.TTS_CREATION.value}"
        self.group_name = "tts_workers"
        # Consumer name includes UUID to identify instances
        self.consumer_name = f"worker-{str(uuid.uuid4())[:8]}"
        
        # Concurrency Control: Max 3 concurrent tasks
        self.semaphore = asyncio.Semaphore(3)
        self.active_tasks: Set[asyncio.Task] = set()
        self.running = False
        
        self.ai_factory = AIProviderFactory()

    async def start(self):
        """워커 시작"""
        logger.info(f"Starting TTS Worker: {self.consumer_name} (Redis: {self.redis_url})")
        
        # Redis Connection
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        
        # Ensure Consumer Group Exists
        try:
            await self.redis.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
            logger.info(f"Consumer group created: {self.group_name}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            logger.info(f"Consumer group already exists: {self.group_name}")
        
        self.running = True
        
        try:
            while self.running:
                # 1. Acquire Semaphore Slot
                # 빈 슬롯이 생길 때까지 대기
                await self.semaphore.acquire()
                
                try:
                    # 2. Read from Redis (Blocking for 1s)
                    # 한 번에 1개씩만 가져와서 태스크로 실행 (세마포어 루프 구조상 1개씩 처리하는게 깔끔함)
                    messages = await self.redis.xreadgroup(
                        self.group_name,
                        self.consumer_name,
                        {self.stream_name: ">"},
                        count=1,
                        block=1000
                    )
                    
                    if not messages:
                        # 메시지가 없으면 슬롯 반환하고 다시 대기
                        self.semaphore.release()
                        continue
                    
                    # 3. Process Messages
                    for stream, msgs in messages:
                        for msg_id, data in msgs:
                            logger.info(f"Received message: {msg_id}")
                            
                            # Fire and forget (bg task) - Semaphore is held!
                            task = asyncio.create_task(self.process_message_wrapper(msg_id, data))
                            self.active_tasks.add(task)
                            
                            # Cleanup callback
                            task.add_done_callback(self.active_tasks.discard)
                            
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    self.semaphore.release()
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        finally:
            await self.shutdown()

    async def process_message_wrapper(self, msg_id, data):
        """메시지 처리 래퍼 (세마포어 반환 보장)"""
        try:
            await self.process_message(msg_id, data)
        finally:
            # 작업이 끝나면 반드시 세마포어 반환
            self.semaphore.release()

    async def process_message(self, msg_id, data):
        """실제 메시지 처리 로직"""
        try:
            # 1. Parse Event
            event_json = data.get("event")
            if not event_json:
                logger.error(f"Invalid message format (missing 'event'): {data}")
                # 형식이 잘못된 메시지는 ACK 처리하여 다시 안 받음 (Dead Letter Queue 개념이 없으므로 Log만)
                await self.redis.xack(self.stream_name, self.group_name, msg_id)
                return

            event_dict = json.loads(event_json)
            payload = event_dict.get("payload", {})
            
            uuid_str = payload.get("uuid")
            text = payload.get("text")
            
            if not uuid_str or not text:
                logger.error(f"Invalid payload (missing uuid/text): {payload}")
                await self.redis.xack(self.stream_name, self.group_name, msg_id)
                return

            # 2. Process Logic
            await self.handle_tts_task(uuid_str, text)
            
            # 3. ACK
            await self.redis.xack(self.stream_name, self.group_name, msg_id)
            logger.info(f"Task successfully processed and ACKed: {msg_id}")
            
        except Exception as e:
            logger.error(f"Failed to process message {msg_id}: {e}", exc_info=True)
            # 실패 시 ACK 안함 -> 나중에 재처리 (XCLAIM 등 필요하지만 여기선 생략)

    async def handle_tts_task(self, dialogue_audio_id_str: str, text: str):
        """DB 조회, API 호출, 파일 저장"""
        async with AsyncSessionLocal() as session:
            try:
                # 1. DB Lookup
                audio_id = uuid.UUID(dialogue_audio_id_str)
                stmt = select(DialogueAudio).where(DialogueAudio.id == audio_id)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                
                if not record:
                    logger.error(f"DialogueAudio record not found: {audio_id}")
                    return

                # Update Status: PROCESSING
                record.status = "PROCESSING"
                await session.commit()
                
                # 2. Call ElevenLabs API
                provider = self.ai_factory.get_tts_provider()
                # voice_id가 없으면 Provider 기본값 사용되지만, DB에 저장된 voice_id 사용
                voice_id = record.voice_id
                
                try:
                    audio_bytes = await provider.text_to_speech(
                        text=text,
                        voice_id=voice_id
                    )
                except Exception as api_error:
                    logger.error(f"API Error: {api_error}")
                    record.status = "FAILED"
                    await session.commit()
                    return

                # 3. Save to File
                # record.audio_url stores the relative path e.g., "shared/books/..."
                target_path = record.audio_url.strip("/")
                full_path = os.path.join(settings.storage_base_path, target_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                async with aiofiles.open(full_path, "wb") as f:
                    await f.write(audio_bytes)
                
                logger.info(f"File saved: {full_path}")

                # 4. Update Status: COMPLETED
                record.status = "COMPLETED"
                # Duration은 mp3 파싱 필요하므로 생략 (또는 provider가 반환하면 좋음)
                await session.commit()
                
            except Exception as e:
                logger.error(f"DB/File Error during task: {e}", exc_info=True)
                # Rollback handled by context manager if not committed, 
                # but we committed explicitly.
                # If verify fails, explicitly set FAILED?
                # We do minimal implementation here.
                raise

    async def shutdown(self):
        """종료 처리"""
        logger.info("Shutting down worker...")
        if self.redis:
            await self.redis.close()
        
        # Cancel active tasks
        if self.active_tasks:
            for task in self.active_tasks:
                task.cancel()
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

if __name__ == "__main__":
    worker = TTSWorker()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
        loop.run_until_complete(worker.shutdown())
