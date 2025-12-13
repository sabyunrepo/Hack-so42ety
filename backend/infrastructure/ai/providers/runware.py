"""
Runware Video Provider
Runware API를 사용한 비디오 생성
"""

import uuid
import base64
import logging
from typing import Optional, Dict, Any
from io import BytesIO
import httpx
from PIL import Image

from ..base import VideoGenerationProvider, ImageGenerationProvider
from ....core.config import settings

logger = logging.getLogger(__name__)

class RunwareProvider(VideoGenerationProvider, ImageGenerationProvider):
    """
    Runware Video Provider

    Runware API를 사용하여 이미지로부터 비디오를 생성
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Runware API Key (None일 경우 settings에서 가져옴)
        """
        self.api_key = api_key or settings.runware_api_key
        self.base_url = settings.runware_api_url
        self.timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)

    async def generate_image(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        quality: str = "standard",
        style: Optional[str] = None,
    ) -> bytes:
        """
        이미지 생성 (Runware REST API)

        Args:
            prompt: 이미지 생성 프롬프트
            width: 이미지 너비 (기본값: 512)
            height: 이미지 높이 (기본값: 512)
            quality: 품질 (standard, hd) - 현재 미사용
            style: 스타일 (vivid, natural 등) - 현재 미사용

        Returns:
            bytes: 생성된 이미지 바이너리 데이터

        Raises:
            httpx.HTTPStatusError: API 요청 실패
            KeyError: 응답 형식 오류
        """
        task_uuid = str(uuid.uuid4())

        # REST API 페이로드 (배열 형태)
        payload = [
            {
                "taskType": "imageInference",
                "taskUUID": task_uuid,
                "positivePrompt": prompt,
                "width": width,
                "height": height,
                "model": "civitai:102438@133677",
                "numberResults": 1
            }
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            # 에러 체크
            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Runware image generation failed: {error_msg}")
                raise Exception(f"Runware API error: {error_msg}")

            # 응답에서 이미지 URL 추출
            if "data" not in result or len(result["data"]) == 0:
                raise Exception("No image data in response")

            image_data = result["data"][0]
            image_url = image_data.get("imageURL")

            if not image_url:
                raise Exception("No imageURL in response")

            print(f"Runware image generated: {image_url}")

            # 이미지 다운로드
            image_response = await client.get(image_url)
            image_response.raise_for_status()

            return image_response.content

    async def generate_images_batch(
        self,
        prompts: list[str],
        width: int = 512,
        height: int = 512,
    ) -> list[bytes]:
        """
        여러 이미지 배치 생성

        Args:
            prompts: 이미지 프롬프트 리스트
            width: 이미지 너비
            height: 이미지 높이

        Returns:
            List[bytes]: 생성된 이미지 바이너리 데이터 리스트
        """
        # 각 프롬프트에 대해 순차적으로 이미지 생성
        images = []
        for prompt in prompts:
            image_bytes = await self.generate_image(prompt, width, height)
            images.append(image_bytes)
        return images

    async def generate_image_from_image(
        self,
        image_data: bytes,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
        strength: Optional[float] = None,
        cfg_scale: Optional[float] = None,
        steps: Optional[int] = None,
    ) -> bytes:
        """
        이미지-to-이미지 생성 (Runware Image-to-Image API)

        Args:
            image_data: 입력 이미지 바이너리
            prompt: 이미지 생성 프롬프트
            width: 너비 (기본값: 1024)
            height: 높이 (기본값: 1024)
            style: 스타일 (현재 미사용)
            strength: 변환 강도 (0.0-1.0, 기본값: 0.7, 권장: 0.7-0.9)
            cfg_scale: 프롬프트 가이드 강도 (기본값: 7.0, 범위: 1.0-20.0)
            steps: 디노이징 스텝 (기본값: 30, 범위: 1-50)

        Returns:
            bytes: 생성된 이미지 바이너리 데이터

        Raises:
            httpx.HTTPStatusError: API 요청 실패
            Exception: 응답 형식 오류 또는 API 에러
        """
        task_uuid = str(uuid.uuid4())
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # 설정에서 기본값 가져오기 (없으면 전달된 인자 사용)
        strength = strength if strength is not None else settings.runware_img2img_strength
        cfg_scale = cfg_scale if cfg_scale is not None else settings.runware_img2img_cfg_scale
        steps = steps if steps is not None else settings.runware_img2img_steps

        # REST API 페이로드 (배열 형태)
        payload = [
            {
                "taskType": "imageInference",
                "taskUUID": task_uuid,
                "positivePrompt": prompt,
                "seedImage": f"data:image/png;base64,{image_base64}",  # 이미지를 seedImage로 사용
                "strength": strength,          # 변환 강도 (0.0-1.0)
                "CFGScale": cfg_scale,         # 프롬프트 가이드 스케일
                "steps": steps,                # 디노이징 스텝 수
                "width": width,
                "height": height,
                "model": settings.runware_img2img_model,
                "numberResults": 1
            }
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            # 에러 체크
            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Runware image-to-image failed: {error_msg}")
                raise Exception(f"Runware API error: {error_msg}")

            # 응답에서 이미지 URL 추출
            if "data" not in result or len(result["data"]) == 0:
                raise Exception("No image data in response")

            image_data_result = result["data"][0]
            image_url = image_data_result.get("imageURL")

            if not image_url:
                raise Exception("No imageURL in response")

            print(f"Runware image-to-image generated: {image_url}, "
                       f"strength={strength}, CFGScale={cfg_scale}, steps={steps}")

            # 이미지 다운로드
            image_response = await client.get(image_url)
            image_response.raise_for_status()

            return image_response.content

    async def generate_video(
        self,
        image_data: bytes,
        prompt: Optional[str] = None,
        duration: int = 5,
        width: int = 720,
        height: int = 720,
        fps: Optional[int] = None,
        output_format: str = "mp4",
        output_quality: int = 95,
    ) -> str:
        """
        비디오 생성 작업 시작 (Image-to-Video)

        Args:
            image_data: 입력 이미지 바이너리 데이터
            prompt: 비디오 생성 프롬프트 (옵션)
            duration: 비디오 길이 (초, 기본값: 5, 범위: 1-10)
            width: 비디오 너비 (기본값: 1920, 8의 배수 필수)
            height: 비디오 높이 (기본값: 1080, 8의 배수 필수)
            fps: 프레임률 (옵션, 모델 기본값 사용, 범위: 15-60)
            output_format: 출력 형식 (mp4, webm)
            output_quality: 출력 품질 (20-99, 기본값: 95)

        Returns:
            str: task_uuid (Runware task ID)

        Raises:
            ValueError: 파라미터 검증 실패
            Exception: API 에러
        """
        # 파라미터 검증
        if width % 8 != 0 or height % 8 != 0:
            raise ValueError(f"width and height must be multiples of 8. Got: {width}x{height}")

        if not (1 <= duration <= 10):
            raise ValueError(f"duration must be between 1 and 10 seconds. Got: {duration}")

        if fps is not None and not (15 <= fps <= 60):
            raise ValueError(f"fps must be between 15 and 60. Got: {fps}")

        if output_quality < 20 or output_quality > 99:
            raise ValueError(f"output_quality must be between 20 and 99. Got: {output_quality}")

        task_uuid = str(uuid.uuid4())

        #test
        model = 'klingai:6@0'
        # "width": width,
        # "height": height,
        # Payload 기본 구조
        payload = [{
            "taskType": "videoInference",
            "taskUUID": task_uuid,
            "positivePrompt": prompt or "animate this image naturally with smooth motion",
            "model": model,
            "duration": duration,

            "outputFormat": output_format,
            "outputQuality": output_quality,
            "deliveryMethod": "async",
            "includeCost": True,
            "numberResults": 1,
        }]

        # 이미지가 제공된 경우: Image-to-Video (frameImages 추가)
        if image_data is not None:
            payload[0]["frameImages"] = [
                {
                    "inputImage": f"data:image/png;base64,{image_data}",
                    "frame": "first"  # 첫 프레임에 이미지 배치
                }
            ]
            print(f"Mode: Image-to-Video (frameImages included, resized)")
        else:
            # 이미지가 없는 경우: Text-to-Video
            print(f"Mode: Text-to-Video (no frameImages)")

        # FPS가 지정된 경우 추가
        if fps is not None:
            payload[0]["fps"] = fps

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            print("payload:", payload)
            print("self.base_url:", self.base_url)
            print("self.api_key:", self.api_key)

            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                print("API Response:", result)

                # 에러 체크
                if "errors" in result and len(result["errors"]) > 0:
                    error = result["errors"][0]
                    error_msg = error.get("message", "Unknown error")
                    error_code = error.get("code", "unknown")
                    error_param = error.get("parameter", "unknown")

                    logger.error(f"Runware video generation failed: [{error_code}] {error_msg} (parameter: {error_param})")
                    print(f"Full error object: {error}")
                    raise Exception(f"Runware API error [{error_code}]: {error_msg} (parameter: {error_param})")

            except httpx.HTTPStatusError as e:
                # HTTP 에러 발생 시 응답 본문 출력
                error_detail = e.response.text
                print(f"HTTP Status Error: {e.response.status_code}")
                print(f"Error Response Body: {error_detail}")
                raise Exception(f"HTTP {e.response.status_code}: {error_detail}")

        print(f"Runware video generation started: task_uuid={task_uuid}, "
                   f"duration={duration}s, size={width}x{height}")
        return task_uuid

    async def check_video_status(self, task_id: str) -> Dict[str, Any]:
        """
        비디오 생성 상태 확인 (getResponse)

        Args:
            task_id: 작업 ID

        Returns:
            Dict[str, Any]: {
                "status": str,  # pending, processing, completed, failed
                "progress": int,  # 0~100
                "video_url": Optional[str],
                "error": Optional[str]
            }
        """
        payload = [{
            "taskType": "getResponse",
            "taskUUID": task_id
        }]

        print(f"[check_video_status] Checking status for task_id: {task_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                print(f"[check_video_status] API Response: {result}")

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                print(f"[check_video_status] HTTP Status Error: {e.response.status_code}")
                print(f"[check_video_status] Error Response Body: {error_detail}")
                # 에러 발생 시에도 processing으로 반환 (재시도 허용)
                return {
                    "status": "processing",
                    "progress": 50,
                    "video_url": None,
                    "error": None
                }
            except Exception as e:
                print(f"[check_video_status] Unexpected error: {type(e).__name__}: {str(e)}")
                return {
                    "status": "processing",
                    "progress": 50,
                    "video_url": None,
                    "error": None
                }

        # Response 파싱 - Runware API는 {"data": [...]} 형태로 응답
        if not result:
            print(f"[check_video_status] Empty result, status: processing")
            return {"status": "processing", "progress": 50, "video_url": None, "error": None}

        # 에러 체크
        if "errors" in result and len(result["errors"]) > 0:
            error = result["errors"][0]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", "unknown")
            print(f"[check_video_status] API returned error: [{error_code}] {error_msg}")
            return {
                "status": "failed",
                "progress": 0,
                "video_url": None,
                "error": f"[{error_code}] {error_msg}"
            }

        # data 배열 확인
        if "data" not in result or len(result["data"]) == 0:
            print(f"[check_video_status] No data in result, status: processing")
            return {"status": "processing", "progress": 50, "video_url": None, "error": None}

        task_result = result["data"][0]
        print(f"[check_video_status] Task result: {task_result}")

        # 완료 체크 - videoURL이 있으면 완료
        if "videoURL" in task_result:
            video_url = task_result["videoURL"]
            print(f"[check_video_status] Video completed! URL: {video_url}")
            return {
                "status": "completed",
                "progress": 100,
                "video_url": video_url,
                "error": None
            }
        # status 필드 체크 (processing 중일 때)
        elif "status" in task_result:
            status = task_result["status"]
            print(f"[check_video_status] Task status: {status}")
            if status == "processing":
                return {"status": "processing", "progress": 50, "video_url": None, "error": None}
            elif status == "failed":
                error_msg = task_result.get("error", "Unknown error")
                return {
                    "status": "failed",
                    "progress": 0,
                    "video_url": None,
                    "error": error_msg
                }
            else:
                # 알 수 없는 상태
                print(f"[check_video_status] Unknown status: {status}")
                return {"status": "processing", "progress": 50, "video_url": None, "error": None}
        else:
            # status도 videoURL도 없으면 아직 처리 중
            print(f"[check_video_status] No status or videoURL, assuming processing...")
            return {"status": "processing", "progress": 50, "video_url": None, "error": None}

    async def download_video(self, video_url: str) -> bytes:
        """
        생성된 비디오 다운로드

        Args:
            video_url: 비디오 URL

        Returns:
            bytes: 비디오 바이너리 데이터
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            return response.content
