"""
Video Generator Service Module
비디오 생성 (GenAI + 템플릿 복사) 전담 서비스
"""

import shutil
import asyncio
import base64
import time
from typing import List, Optional, TYPE_CHECKING
from pathlib import Path
from io import BytesIO
from fastapi import UploadFile
import httpx

from ..core.config import settings
from ..core.logging import get_logger
from ..prompts.generate_video_prompt import GenerateVideoPrompt
from ..storage import AbstractStorageService

if TYPE_CHECKING:
    from ..core.key_pool_manager import AbstractKeyPoolManager
    from ..core.jwt_auth import KlingJWTAuth

logger = get_logger(__name__)


class VideoGeneratorService:
    """비디오 생성 서비스 (Kling API + 템플릿 복사)"""

    def __init__(
        self,
        storage_service: AbstractStorageService,
        image_data_dir: str,
        video_data_dir: str,
        kling_client: Optional[httpx.AsyncClient] = None,
        kling_semaphore: Optional[asyncio.Semaphore] = None,
        key_pool_manager: Optional["AbstractKeyPoolManager"] = None,
        kling_jwt_auth: Optional["KlingJWTAuth"] = None,
        template_book_id: Optional[str] = None,
        template_video: Optional[str] = None,
    ):
        """
        VideoGeneratorService 초기화

        Args:
            storage_service: 스토리지 서비스 (비디오 업로드용)
            image_data_dir: 이미지 데이터 디렉토리 경로
            video_data_dir: 비디오 데이터 디렉토리 경로
            kling_client: Kling API 클라이언트 (선택적)
            kling_semaphore: Kling API 동시성 제어 세마포어 (선택적)
            key_pool_manager: 키 풀 관리자 (선택적)
            kling_jwt_auth: JWT 인증 핸들러 (선택적)
            template_book_id: 템플릿 Book ID (테스트용)
            template_video: 템플릿 비디오 파일명 (테스트용)
        """
        self.storage = storage_service
        self.image_data_dir = image_data_dir
        self.video_data_dir = video_data_dir
        self.kling_client = kling_client
        self.kling_semaphore = kling_semaphore
        self.key_pool_manager = key_pool_manager
        self.kling_jwt_auth = kling_jwt_auth
        self.template_book_id = template_book_id or settings.template_book_id
        self.template_video = template_video or settings.template_video

        if kling_client and key_pool_manager and kling_jwt_auth:
            logger.info(
                "VideoGeneratorService initialized with Kling API client, "
                "key pool manager, and JWT auth"
            )
        elif kling_client:
            logger.warning(
                "VideoGeneratorService initialized with Kling API client but without "
                "key pool manager or JWT auth"
            )
        else:
            logger.warning(
                "VideoGeneratorService initialized without Kling API client - template mode only"
            )

    async def generate_video_from_template(
        self, index: int, story: List[str], image_url: str, book_id: str, page_id: str
    ) -> str:
        """
        템플릿 비디오를 복사하여 페이지 비디오 생성 (테스트용)

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열 (미사용)
            image_url: 생성된 이미지 URL (미사용)
            book_id: Book ID
            page_id: Page ID

        Returns:
            str: 복사된 비디오 URL
        """
        logger.info(
            f"[VideoGeneratorService] Copying template video for page {index + 1}"
        )
        try:
            # 템플릿 비디오 경로
            template_path = (
                Path(self.video_data_dir) / self.template_book_id / self.template_video
            )

            # 대상 디렉토리 생성
            target_dir = Path(self.video_data_dir) / book_id
            target_dir.mkdir(parents=True, exist_ok=True)

            # 대상 파일 경로
            target_filename = f"{page_id}.mp4"
            target_path = target_dir / target_filename

            # 파일 복사
            shutil.copy2(template_path, target_path)

            # URL 생성
            video_url = f"/data/video/{book_id}/{target_filename}"

            logger.info(f"[VideoGeneratorService] Template video copied: {video_url}")
            return video_url

        except Exception as e:
            logger.error(
                f"[VideoGeneratorService] Template video copy failed for page {index + 1}: {e}",
                exc_info=True,
            )
            return ""

    async def generate_video_with_kling(
        self, index: int, story: List[str], image_url: str, book_id: str, page_id: str
    ) -> str:
        """
        Kling API를 호출하여 페이지 비디오 생성 및 업로드 (재시도 로직 포함)

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열
            image_url: 생성된 이미지 URL (로컬 경로)
            book_id: Book ID
            page_id: Page ID

        Returns:
            str: 업로드된 비디오 URL (성공 시) 또는 빈 문자열 (실패 시)
        """
        if not self.kling_client:
            logger.error("Kling API client is not initialized")
            return ""

        if not self.kling_semaphore:
            logger.error("Kling semaphore is not initialized")
            return ""

        if not self.key_pool_manager:
            logger.error("Key pool manager is not initialized")
            return ""

        logger.info(
            f"[VideoGeneratorService] Generating video with Kling API for page {index + 1}"
        )

        # 최대 재시도 횟수 = 사용 가능한 키 개수
        max_retries = len(self.key_pool_manager.get_all_key_pairs())

        for attempt in range(max_retries):
            try:
                return await self._generate_video_with_kling_attempt(
                    index, story, image_url, book_id, page_id, attempt + 1, max_retries
                )

            except httpx.HTTPStatusError as e:
                # 응답 데이터 파싱
                try:
                    response_data = e.response.json()
                except:
                    response_data = {}

                # 키 관련 에러 체크 (재시도 가능)
                # 1. 429 Rate Limit
                # 2. 401 Unauthorized (access key disabled, invalid key 등)
                # 3. API code 1002 (access key is disabled)
                should_retry = False
                error_reason = ""

                if e.response.status_code == 429:
                    if self.key_pool_manager.is_rate_limit_error(429, response_data):
                        should_retry = True
                        error_reason = "Rate Limit (429)"
                elif e.response.status_code == 401:
                    # 401은 보통 키 문제이므로 다른 키로 재시도
                    should_retry = True
                    error_reason = "Unauthorized (401) - Invalid/Disabled Key"
                elif response_data.get("code") == 1002:
                    # API 레벨 에러 코드 1002: access key is disabled
                    should_retry = True
                    error_reason = "API Error 1002 - Access Key Disabled"

                if should_retry:
                    logger.warning(
                        f"🔄 {error_reason} detected (attempt {attempt + 1}/{max_retries})"
                    )
                    self.key_pool_manager.mark_key_failed(
                        f"{error_reason}: {e.response.text[:200]}"
                    )

                    # JWT 토큰 무효화 (다음 요청에서 새 키로 재생성)
                    if self.kling_jwt_auth:
                        self.kling_jwt_auth.invalidate_token()

                    # 마지막 시도가 아니면 계속
                    if attempt < max_retries - 1:
                        logger.info(f"⏭️ Retrying with next key...")
                        continue
                    else:
                        logger.error("❌ All API keys exhausted. Video generation failed.")
                        return ""

                # 재시도 불가능한 HTTP 에러는 즉시 실패
                logger.error(
                    f"[VideoGeneratorService] Non-retryable HTTP error for page {index + 1}: "
                    f"{e.response.status_code} - {e.response.text}",
                    exc_info=True,
                )
                return ""

            except Exception as e:
                logger.error(
                    f"[VideoGeneratorService] Kling video generation failed for page {index + 1}: {e}",
                    exc_info=True,
                )
                return ""

        # 모든 재시도 실패
        logger.error("❌ All API keys exhausted. Video generation failed.")
        return ""

    async def _generate_video_with_kling_attempt(
        self,
        index: int,
        story: List[str],
        image_url: str,
        book_id: str,
        page_id: str,
        attempt: int,
        max_retries: int,
    ) -> str:
        """
        Kling API 단일 시도 (내부 메서드)

        Returns:
            str: 업로드된 비디오 URL (성공 시)

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
            Exception: 기타 에러 발생 시
        """
        # 1. 이미지 URL을 로컬 파일 경로로 변환
        image_path = Path(self.image_data_dir) / image_url.replace("/data/image/", "")

        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # 2. 이미지를 Base64로 인코딩
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

        # 3. 비디오 생성 프롬프트
        prompt = GenerateVideoPrompt(stories=story).render()

        # 4. Kling API 작업 생성 및 폴링 (세마포어로 동시성 제어)
        async with self.kling_semaphore:
            logger.info(
                f"[VideoGeneratorService] 🔑 Using key (attempt {attempt}/{max_retries}). "
                f"Creating Kling task for page {index + 1}..."
            )

            # 4-1. 작업 생성 요청
            create_response = await self.kling_client.post(
                f"{settings.kling_api_url}/v1/videos/image2video",
                json={
                    "model_name": settings.kling_model_name,
                    "image": base64_image,
                    "prompt": prompt,
                    "mode": settings.kling_video_mode,
                    "duration": settings.kling_video_duration,
                },
            )

            # 4-2. 응답 검증
            create_response.raise_for_status()
            create_data = create_response.json()

            # API 레벨 에러 체크 (code != 0)
            if create_data.get("code") != 0:
                error_code = create_data.get("code")
                error_msg = create_data.get("message", "Unknown error")

                # Rate Limit 에러인지 확인
                if self.key_pool_manager.is_rate_limit_error(
                    create_response.status_code, create_data
                ):
                    logger.warning(
                        f"🔄 API-level Rate Limit on task creation (code {error_code})"
                    )
                    self.key_pool_manager.mark_key_failed(
                        f"Task creation - Code {error_code}: {error_msg}"
                    )
                    # HTTPStatusError로 변환하여 외부 재시도 로직으로 전달
                    raise httpx.HTTPStatusError(
                        f"Rate limit error: {error_msg}",
                        request=create_response.request,
                        response=create_response,
                    )

                # 다른 API 에러는 즉시 실패
                logger.error(
                    f"[VideoGeneratorService] Kling API error (code {error_code}): {error_msg}"
                )
                raise Exception(f"Kling API error (code {error_code}): {error_msg}")

            task_id = create_data["data"]["task_id"]
            logger.info(
                f"[VideoGeneratorService] ✅ Kling task created: {task_id} for page {index + 1}"
            )

            # 4-3. Non-blocking Polling (세마포어 유지하면서)
            start_time = time.time()
            max_polling_time = settings.kling_max_polling_time

            while True:
                # 타임아웃 체크
                elapsed_time = time.time() - start_time
                if elapsed_time > max_polling_time:
                    logger.error(
                        f"[VideoGeneratorService] Polling timeout ({max_polling_time}s) "
                        f"for task {task_id}"
                    )
                    raise Exception(f"Polling timeout for task {task_id}")

                # Non-blocking sleep (다른 코루틴 실행 허용)
                await asyncio.sleep(settings.kling_polling_interval)

                # 상태 확인
                status_response = await self.kling_client.get(
                    f"{settings.kling_api_url}/v1/videos/image2video/{task_id}"
                )
                status_response.raise_for_status()
                status_data = status_response.json()

                # API 레벨 에러 체크 (폴링 중)
                if status_data.get("code") != 0:
                    error_code = status_data.get("code")
                    error_msg = status_data.get("message", "Unknown error")

                    # Rate Limit 에러인지 확인
                    if self.key_pool_manager.is_rate_limit_error(
                        status_response.status_code, status_data
                    ):
                        logger.warning(
                            f"🔄 API-level Rate Limit during polling (code {error_code})"
                        )
                        self.key_pool_manager.mark_key_failed(
                            f"Polling - Code {error_code}: {error_msg}"
                        )
                        raise httpx.HTTPStatusError(
                            f"Rate limit error during polling: {error_msg}",
                            request=status_response.request,
                            response=status_response,
                        )

                    # 다른 API 에러는 즉시 실패
                    logger.error(
                        f"[VideoGeneratorService] Kling status check error: {error_msg}"
                    )
                    raise Exception(
                        f"Status check error (code {error_code}): {error_msg}"
                    )

                task_status = status_data["data"]["task_status"]
                logger.info(
                    f"[VideoGeneratorService] Task {task_id} status: {task_status} "
                    f"(elapsed: {elapsed_time:.1f}s)"
                )

                if task_status == "succeed":
                    # 성공: 비디오 URL 추출
                    videos = status_data["data"]["task_result"]["videos"]
                    if not videos:
                        logger.error("No videos in task result")
                        raise Exception("No videos in task result")

                    kling_video_url = videos[0]["url"]
                    logger.info(
                        f"[VideoGeneratorService] ✅ Video generation succeeded: {kling_video_url}"
                    )
                    break

                elif task_status == "failed":
                    # 실패
                    error_msg = status_data["data"].get(
                        "task_status_msg", "Unknown error"
                    )
                    logger.error(
                        f"[VideoGeneratorService] Video generation failed: {error_msg}"
                    )
                    raise Exception(f"Video generation failed: {error_msg}")

                # submitted 또는 processing 상태면 계속 폴링

            # 5. Kling URL에서 비디오 다운로드
            logger.info(
                f"[VideoGeneratorService] Downloading video from Kling: {kling_video_url}"
            )
            video_response = await self.kling_client.get(kling_video_url)
            video_response.raise_for_status()
            video_bytes = video_response.content

            # 6. UploadFile 객체 생성
            video_file = UploadFile(
                file=BytesIO(video_bytes),
                filename=f"{page_id}.mp4",
                headers={"content-type": "video/mp4"},
            )

            # 7. Storage Service로 업로드
            video_url = await self.storage.upload_file(
                file=video_file,
                book_id=book_id,
                filename=video_file.filename,
                media_type="video",
            )

            logger.info(
                f"[VideoGeneratorService] 🎬 Video uploaded successfully: {video_url} "
                f"(page {index + 1})"
            )
            return video_url

        # 세마포어 자동 해제 (async with 종료)
