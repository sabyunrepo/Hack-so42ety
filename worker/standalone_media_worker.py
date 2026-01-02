#!/usr/bin/env python3
"""
Standalone Media Optimization Worker (Production-Ready)

프로덕션 환경을 위한 개선된 미디어 최적화 워커
- Graceful Shutdown
- Connection Pooling
- 모니터링 메트릭
- XCLAIM 재시도
- Health Check
"""

import asyncio
import json
import logging
import os
import signal
import uuid
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Any
import io

import redis.asyncio as aioredis
from PIL import Image
import boto3
from aiohttp import web

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class R2Storage:
    """Cloudflare R2 Storage 클라이언트 (S3 호환 API 사용)"""
    
    def __init__(self):
        self.client = boto3.client(
            's3',  # S3 호환 API
            endpoint_url=os.getenv("R2_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        )
        self.bucket = os.getenv("R2_BUCKET_NAME", "moriai-storybook-prod")
    
    async def get(self, path: str) -> bytes:
        """파일 다운로드"""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.get_object(Bucket=self.bucket, Key=path)
        )
        return response['Body'].read()
    
    async def save(self, file_data: bytes, path: str, content_type: str):
        """파일 업로드"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=file_data,
                ContentType=content_type
            )
        )


class MediaOptimizationWorker:
    """
    미디어 최적화 워커 (Production-Ready)
    
    최신 워커 패턴 적용:
    - Graceful Shutdown: 안전한 종료
    - Connection Pooling: 성능 향상
    - 모니터링 메트릭: 운영 가시성
    - XCLAIM 재시도: Stuck 메시지 복구
    - Health Check: Kubernetes 통합
    """
    
    def __init__(self):
        # Redis 설정
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.stream_name = "events:media.optimization"
        self.group_name = "media_workers"
        self.consumer_name = f"worker-{str(uuid.uuid4())[:8]}"
        
        # Semaphore (동시성 제어)
        self.image_semaphore = asyncio.Semaphore(10)  # 이미지: 10개
        self.video_semaphore = asyncio.Semaphore(5)   # 비디오: 5개
        
        # Connection Pool
        self.redis_pool = None
        self.redis = None
        
        # Storage
        self.storage = R2Storage()
        
        # State
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.active_tasks: Set[asyncio.Task] = set()
        
        # Metrics
        self.metrics: Dict[str, int] = {
            'processed': 0,
            'failed': 0,
            'image_count': 0,
            'video_count': 0,
        }
    
    async def start(self):
        """워커 시작"""
        logger.info(
            f"Starting Media Optimization Worker: {self.consumer_name}",
            extra={"redis_url": self.redis_url}
        )
        
        # Connection Pool 생성
        self.redis_pool = aioredis.ConnectionPool.from_url(
            self.redis_url,
            max_connections=20,
            decode_responses=True
        )
        self.redis = aioredis.Redis(connection_pool=self.redis_pool)
        
        # Consumer Group 생성
        try:
            await self.redis.xgroup_create(
                self.stream_name,
                self.group_name,
                id="0",
                mkstream=True
            )
            logger.info(f"Consumer group created: {self.group_name}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            logger.info(f"Consumer group already exists: {self.group_name}")
        
        # Signal handlers 등록 (Graceful Shutdown)
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.graceful_shutdown())
            )
        
        # 백그라운드 작업 시작
        asyncio.create_task(self.periodic_claim_pending())
        asyncio.create_task(self.log_metrics())
        asyncio.create_task(self.start_health_server())
        
        self.running = True
        
        try:
            while self.running and not self.shutdown_event.is_set():
                # Read from Redis (Blocking for 1s)
                messages = await self.redis.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    {self.stream_name: ">"},
                    count=1,
                    block=1000
                )
                
                if not messages:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process Messages
                for stream, msgs in messages:
                    for msg_id, data in msgs:
                        logger.info(
                            f"Received message: {msg_id}",
                            extra={"stream": stream, "data": data}
                        )
                        
                        # Fire and forget (bg task)
                        task = asyncio.create_task(
                            self.process_message_wrapper(msg_id, data)
                        )
                        self.active_tasks.add(task)
                        task.add_done_callback(self.active_tasks.discard)
        
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        finally:
            await self.shutdown()
    
    async def graceful_shutdown(self):
        """Graceful shutdown - 진행 중인 작업 완료 대기"""
        logger.info("Graceful shutdown initiated...")
        self.running = False
        self.shutdown_event.set()
        
        # 진행 중인 작업 완료 대기 (최대 30초)
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} tasks to complete...")
            done, pending = await asyncio.wait(
                self.active_tasks,
                timeout=30.0
            )
            
            if pending:
                logger.warning(f"{len(pending)} tasks did not complete, cancelling...")
                for task in pending:
                    task.cancel()
    
    async def process_message_wrapper(self, msg_id: str, data: Dict[str, Any]):
        """메시지 처리 래퍼 (메트릭 수집)"""
        try:
            await self.process_message(msg_id, data)
            self.metrics['processed'] += 1
        except Exception as e:
            self.metrics['failed'] += 1
            logger.error(f"Failed to process message {msg_id}: {e}", exc_info=True)
    
    async def process_message(self, msg_id: str, data: Dict[str, Any]):
        """실제 메시지 처리 로직"""
        try:
            # 1. Parse Event
            event_json = data.get("event")
            if not event_json:
                logger.error(f"Invalid message format (missing 'event'): {data}")
                await self.redis.xack(self.stream_name, self.group_name, msg_id)
                return
            
            event_dict = json.loads(event_json)
            payload = event_dict.get("payload", {})
            
            task_type = payload.get("type")
            if not task_type:
                logger.error(f"Invalid payload (missing type): {payload}")
                await self.redis.xack(self.stream_name, self.group_name, msg_id)
                return
            
            # 2. Process by Type
            if task_type == "image_webp":
                async with self.image_semaphore:
                    await self.handle_image_optimization(payload)
                self.metrics['image_count'] += 1
            elif task_type == "video_compress":
                async with self.video_semaphore:
                    await self.handle_video_optimization(payload)
                self.metrics['video_count'] += 1
            else:
                logger.error(f"Unknown task type: {task_type}")
            
            # 3. ACK
            await self.redis.xack(self.stream_name, self.group_name, msg_id)
            logger.info(f"Task successfully processed and ACKed: {msg_id}")
        
        except Exception as e:
            logger.error(f"Failed to process message {msg_id}: {e}", exc_info=True)
            # 실패 시 ACK 안함 -> 재처리
    
    async def handle_image_optimization(self, payload: Dict[str, Any]):
        """이미지 WebP 변환"""
        input_path = payload.get("input_path")
        output_path = payload.get("output_path")
        file_id = payload.get("file_id")
        
        if not all([input_path, output_path, file_id]):
            logger.error(f"Invalid image payload: {payload}")
            return
        
        try:
            logger.info(f"Converting to WebP: {input_path}")
            
            # 1. R2에서 원본 다운로드
            original_data = await self.storage.get(input_path)
            if not original_data:
                logger.error(f"Failed to download original image: {input_path}")
                return
            
            original_size = len(original_data)
            
            # 2. WebP 변환
            webp_data = await self.convert_to_webp(original_data)
            webp_size = len(webp_data)
            
            # 3. R2에 저장
            await self.storage.save(
                file_data=webp_data,
                path=output_path,
                content_type="image/webp"
            )
            
            reduction = ((original_size - webp_size) / original_size) * 100
            logger.info(
                f"WebP conversion completed: {input_path} -> {output_path}",
                extra={
                    "original_size": original_size,
                    "webp_size": webp_size,
                    "reduction": f"{reduction:.1f}%"
                }
            )
        
        except Exception as e:
            logger.error(f"Image optimization failed: {e}", exc_info=True)
            raise
    
    async def convert_to_webp(self, image_bytes: bytes, quality: int = 85) -> bytes:
        """이미지를 WebP로 변환"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._convert_to_webp_sync,
            image_bytes,
            quality
        )
    
    @staticmethod
    def _convert_to_webp_sync(image_bytes: bytes, quality: int) -> bytes:
        """동기 WebP 변환 (executor에서 실행)"""
        img = Image.open(io.BytesIO(image_bytes))
        
        # RGBA → RGB 변환
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # WebP 저장
        output = io.BytesIO()
        img.save(output, format='WEBP', quality=quality, method=6)
        return output.getvalue()
    
    async def handle_video_optimization(self, payload: Dict[str, Any]):
        """비디오 H.265 압축"""
        input_path = payload.get("input_path")
        output_path = payload.get("output_path")
        file_id = payload.get("file_id")
        
        if not all([input_path, output_path, file_id]):
            logger.error(f"Invalid video payload: {payload}")
            return
        
        try:
            logger.info(f"Compressing video: {input_path}")
            
            # 1. R2에서 원본 다운로드
            original_data = await self.storage.get(input_path)
            if not original_data:
                logger.error(f"Failed to download original video: {input_path}")
                return
            
            original_size = len(original_data)
            
            # 2. H.265 압축
            compressed_data = await self.compress_video(original_data)
            compressed_size = len(compressed_data)
            
            # 3. R2에 저장 (원본 교체)
            await self.storage.save(
                file_data=compressed_data,
                path=output_path,
                content_type="video/mp4"
            )
            
            reduction = ((original_size - compressed_size) / original_size) * 100
            logger.info(
                f"Video compression completed: {input_path} -> {output_path}",
                extra={
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "reduction": f"{reduction:.1f}%"
                }
            )
        
        except Exception as e:
            logger.error(f"Video optimization failed: {e}", exc_info=True)
            raise
    
    async def compress_video(self, video_bytes: bytes) -> bytes:
        """비디오를 H.265로 압축 (Quick Sync 우선)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._compress_video_sync,
            video_bytes
        )
    
    @staticmethod
    def _compress_video_sync(video_bytes: bytes) -> bytes:
        """동기 비디오 압축 (executor에서 실행)"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as input_file:
            input_file.write(video_bytes)
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            # Quick Sync Video 시도
            cmd = [
                'ffmpeg',
                '-hwaccel', 'qsv',
                '-c:v', 'h264_qsv',
                '-i', input_path,
                '-c:v', 'hevc_qsv',
                '-preset', 'medium',
                '-global_quality', '28',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("Video compressed with Quick Sync")
        
        except subprocess.CalledProcessError as e:
            # Quick Sync 실패 시 소프트웨어 폴백
            logger.warning(f"Quick Sync failed, falling back to software encoding: {e.stderr}")
            
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx265',
                '-crf', '28',
                '-preset', 'medium',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info("Video compressed with software encoding")
        
        finally:
            # 압축된 파일 읽기
            with open(output_path, 'rb') as f:
                compressed_data = f.read()
            
            # 임시 파일 삭제
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
        
        return compressed_data
    
    async def periodic_claim_pending(self):
        """주기적 pending 메시지 재처리 (5분마다)"""
        while self.running:
            await asyncio.sleep(300)  # 5분
            try:
                pending = await self.redis.xpending_range(
                    self.stream_name,
                    self.group_name,
                    min="-",
                    max="+",
                    count=10
                )
                
                for msg in pending:
                    # 5분 이상 pending이면 재할당
                    if msg['time_since_delivered'] > 300000:  # 5분 (ms)
                        claimed = await self.redis.xclaim(
                            self.stream_name,
                            self.group_name,
                            self.consumer_name,
                            min_idle_time=300000,
                            message_ids=[msg['message_id']]
                        )
                        
                        for claimed_msg in claimed:
                            logger.info(f"Claimed stuck message: {claimed_msg[0]}")
                            # 재처리
                            await self.process_message(claimed_msg[0], claimed_msg[1])
            
            except Exception as e:
                logger.error(f"Failed to claim pending messages: {e}")
    
    async def log_metrics(self):
        """주기적 메트릭 로깅 (1분마다)"""
        while self.running:
            await asyncio.sleep(60)  # 1분
            logger.info(
                "Worker metrics",
                extra={
                    **self.metrics,
                    'active_tasks': len(self.active_tasks)
                }
            )
    
    async def start_health_server(self):
        """Health check HTTP 서버"""
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/metrics', self.metrics_endpoint)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("Health check server started on :8080")
    
    async def health_check(self, request):
        """Health check 엔드포인트"""
        if self.running and self.redis:
            return web.json_response({'status': 'healthy'})
        return web.json_response({'status': 'unhealthy'}, status=503)
    
    async def metrics_endpoint(self, request):
        """메트릭 엔드포인트"""
        return web.json_response({
            **self.metrics,
            'active_tasks': len(self.active_tasks),
            'consumer_name': self.consumer_name
        })
    
    async def shutdown(self):
        """종료 처리"""
        logger.info("Shutting down worker...")
        if self.redis:
            await self.redis.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
        
        # Cancel active tasks
        if self.active_tasks:
            for task in self.active_tasks:
                task.cancel()
            await asyncio.gather(*self.active_tasks, return_exceptions=True)


if __name__ == "__main__":
    worker = MediaOptimizationWorker()
    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
