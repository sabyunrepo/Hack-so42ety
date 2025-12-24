"""
Runware Video Provider
Runware API를 사용한 비디오 생성
"""

import uuid
import base64
import logging
from typing import Optional, Dict, Any
import httpx

from ..base import VideoGenerationProvider, ImageGenerationProvider
from ....core.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# Model Configuration Dictionaries
# ============================================================

IMAGE_MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "google": {
        "default_width": 896,
        "default_height": 1152,
        "reference_key": "referenceImages",  # Top-level
        "provider_settings": None,
        "output_type": ["dataURI", "URL"],
        "output_format": "PNG",
        "include_cost": True,
        "output_quality": 85,
    },
    "openai:1@2": {  # GPT Image 1 Mini
        "default_width": 1024,
        "default_height": 1024,
        "reference_key": "inputs.referenceImages",  # Nested
        "provider_settings": {"openai": {"quality": "auto", "background": "opaque"}},
        "output_type": ["dataURI", "URL"],
        "output_format": "PNG",
        "include_cost": True,
        "output_quality": 85,
    },
    "openai:4@1": {  # GPT Image 1.5
        "default_width": 1024,
        "default_height": 1536,
        "reference_key": "inputs.referenceImages",
        "provider_settings": {"openai": {"quality": "low", "background": "opaque"}},
        "output_type": ["dataURI", "URL"],
        "output_format": "PNG",
        "include_cost": True,
        "output_quality": 85,
    },
}

VIDEO_MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "klingai": {
        "default_duration": 5,
        "supports_dimensions": False,
        "provider_settings": None,
    },
    "bytedance": {
        "default_duration": 4.0,
        "default_fps": 24,
        "default_width": 832,
        "default_height": 1120,
        "supports_dimensions": True,
        "provider_settings_key": "bytedance",
    },
}


def get_image_config(model_id: str) -> Dict[str, Any]:
    """모델 ID에서 이미지 설정 조회 (부분 매칭 지원)"""
    # 정확한 매칭 먼저
    if model_id in IMAGE_MODEL_CONFIGS:
        return IMAGE_MODEL_CONFIGS[model_id]

    # 부분 매칭
    for key in IMAGE_MODEL_CONFIGS:
        if key in model_id:
            return IMAGE_MODEL_CONFIGS[key]

    # 기본값: google
    return IMAGE_MODEL_CONFIGS["google"]


def get_video_config(model_id: str) -> Dict[str, Any]:
    """모델 ID에서 비디오 설정 조회 (부분 매칭 지원)"""
    for key in VIDEO_MODEL_CONFIGS:
        if key in model_id:
            return VIDEO_MODEL_CONFIGS[key]
    return VIDEO_MODEL_CONFIGS["klingai"]


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
        self.timeout = httpx.Timeout(
            settings.http_timeout, read=settings.http_read_timeout
        )

    async def generate_image(
        self,
        prompt: str,
        width: int = 512,
        height: int = 512,
        quality: str = "standard",  # noqa: ARG002 - kept for API compatibility
        style: Optional[str] = None,  # noqa: ARG002 - kept for API compatibility
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
                "model": settings.runware_img2img_model,
                "numberResults": 1,
            }
        ]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

            result = response.json()

            # 에러 체크
            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                logger.error(
                    f"[Image Task] Runware image generation failed: {error_msg}"
                )
                raise Exception(f"Runware API error: {error_msg}")

            # 응답에서 이미지 URL 추출
            if "data" not in result or len(result["data"]) == 0:
                raise Exception("No image data in response")

            image_data = result["data"][0]
            image_url = image_data.get("imageURL")

            if not image_url:
                raise Exception("No imageURL in response")

            logger.info(f"[Image Task] Runware image generated: {image_url}")

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
        width: Optional[int] = None,
        height: Optional[int] = None,
        style: Optional[str] = None,
        strength: Optional[float] = None,
        cfg_scale: Optional[float] = None,
        steps: Optional[int] = None,
        quality: Optional[str] = None,
        background: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        이미지-to-이미지 생성 (Runware Image-to-Image API) - 모델별 동적 설정 지원

        지원 모델:
            - google:4@1 (Google): referenceImages 최상위 레벨, 864x1184
            - openai:1@2 (GPT Image 1 Mini): inputs.referenceImages, 1024x1024, providerSettings
            - openai:4@1 (GPT Image 1.5): inputs.referenceImages, 1024x1024, providerSettings

        Args:
            image_data: 입력 이미지 바이너리
            prompt: 이미지 생성 프롬프트
            width: 너비 (None이면 모델별 기본값: google=864, openai=1024)
            height: 높이 (None이면 모델별 기본값: google=1184, openai=1024)
            style: 스타일 (현재 미사용)
            strength: 변환 강도 (0.0-1.0, 기본값: 0.7, 권장: 0.7-0.9) - google만
            cfg_scale: 프롬프트 가이드 강도 (기본값: 7.0, 범위: 1.0-20.0) - google만
            steps: 디노이징 스텝 (기본값: 30, 범위: 1-50) - google만
            quality: 품질 설정 (openai만: "auto", "high")
            background: 배경 설정 (openai만: "opaque", "auto", "transparent")

        Returns:
            Dict[str, Any]: Runware API 응답 (data[0].imageUUID, data[0].imageURL 포함)

        Raises:
            httpx.HTTPStatusError: API 요청 실패
            Exception: 응답 형식 오류 또는 API 에러
        """
        # Unused parameters kept for backward compatibility
        _ = (strength, cfg_scale, steps, style, quality, background)

        task_uuid = str(uuid.uuid4())
        image_base64 = base64.b64encode(image_data).decode("utf-8")
        result = None

        model = settings.runware_img2img_model
        config = get_image_config(model)

        # Base payload (common fields)
        payload = [
            {
                "taskType": "imageInference",
                "taskUUID": task_uuid,
                "positivePrompt": prompt,
                "model": model,
                "numberResults": 1,
            }
        ]

        # Apply config-based settings
        payload[0]["width"] = width if width is not None else config["default_width"]
        payload[0]["height"] = height if height is not None else config["default_height"]

        # Reference images (nested or top-level based on config)
        if config["reference_key"] == "inputs.referenceImages":
            payload[0]["inputs"] = {
                "referenceImages": [f"data:image/png;base64,{image_base64}"]
            }
        else:
            payload[0]["referenceImages"] = [f"data:image/png;base64,{image_base64}"]

        # Provider settings
        if config.get("provider_settings"):
            payload[0]["providerSettings"] = config["provider_settings"]

        # Optional output settings (OpenAI specific)
        if config.get("output_type"):
            payload[0]["outputType"] = config["output_type"]
        if config.get("output_format"):
            payload[0]["outputFormat"] = config["output_format"]
        if config.get("include_cost"):
            payload[0]["includeCost"] = config["include_cost"]
        if config.get("output_quality"):
            payload[0]["outputQuality"] = config["output_quality"]

        logger.info(f"[Image Task] Using model: {model}, size: {payload[0]['width']}x{payload[0]['height']}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code >= 400:
                logger.error("[Image Task] Runware API ERROR")
                logger.error(f"[Image Task] Status Code: {response.status_code}")
                logger.error(f"[Image Task] Response Text: {response.text}")

                try:
                    logger.error(f"[Image Task] Response JSON: {response.json()}")
                except Exception:
                    logger.error("[Image Task] Response is not JSON")
                    response.raise_for_status()
                    result = response.json()
                    logger.info(
                        f"[Image Task] Runware image generation response: {result}"
                    )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"[Image Task] Runware image-to-image failed: {error_msg}")
                raise Exception(f"Runware API error: {error_msg}")

            # 응답에서 이미지 데이터 확인
            if "data" not in result or len(result["data"]) == 0:
                raise Exception("No image data in response")

            image_uuid = result["data"][0].get("imageUUID")
            actual_width = payload[0].get("width")
            actual_height = payload[0].get("height")

            logger.info(
                f"[Image Task] Image-to-image completed: model={model}, "
                f"size={actual_width}x{actual_height}, UUID={image_uuid}"
            )

            # JSON 응답 반환 (core.py에서 imageUUID, imageURL 사용)
            return result

    async def generate_video(
        self,
        image_data: Optional[bytes] = None,
        image_uuid: Optional[str] = None,
        prompt: Optional[str] = None,
        duration: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[int] = None,
        output_format: str = "mp4",
        output_quality: int = 95,
        camera_fixed: bool = True,
    ) -> str:
        """
        비디오 생성 작업 시작 (Image-to-Video) - 모델별 동적 설정 지원

        지원 모델:
            - klingai:6@0 (Kling AI): duration만 사용, fps/width/height 미사용
            - bytedance:2@2 (ByteDance Seedance): 모든 파라미터 사용

        Args:
            image_data: 입력 이미지 바이너리 데이터 (base64 인코딩됨)
            image_uuid: Runware 이미지 UUID (image_data보다 우선)
            prompt: 비디오 생성 프롬프트 (옵션, 2-3000자)
            duration: 비디오 길이 (초, None이면 모델별 기본값: klingai=5, bytedance=4)
            width: 비디오 너비 (bytedance만 사용, 기본값: 832)
            height: 비디오 높이 (bytedance만 사용, 기본값: 1120)
            fps: 프레임률 (bytedance만 사용, 기본값: 24)
            output_format: 출력 형식 (mp4, webm)
            output_quality: 출력 품질 (20-99, 기본값: 95)
            camera_fixed: 카메라 고정 여부 (bytedance만 사용, 기본값: True)

        Returns:
            str: task_uuid (Runware task ID)

        Raises:
            ValueError: 파라미터 검증 실패
            Exception: API 에러
        """
        # Validation
        if duration is not None and not (1.2 <= duration <= 12):
            raise ValueError(
                f"duration must be between 1.2 and 12 seconds. Got: {duration}"
            )

        if output_quality < 20 or output_quality > 99:
            raise ValueError(
                f"output_quality must be between 20 and 99. Got: {output_quality}"
            )

        task_uuid = str(uuid.uuid4())
        model = settings.runware_video_model
        config = get_video_config(model)

        # Base payload (common fields)
        payload = [
            {
                "taskType": "videoInference",
                "taskUUID": task_uuid,
                "positivePrompt": prompt
                or "animate this image naturally with smooth motion",
                "model": model,
                "outputFormat": output_format,
                "outputQuality": output_quality,
                "deliveryMethod": "async",
                "includeCost": True,
                "numberResults": 1,
            }
        ]

        # Apply config-based settings
        payload[0]["duration"] = duration if duration is not None else config["default_duration"]

        # Dimensions (only for models that support it)
        if config.get("supports_dimensions"):
            payload[0]["fps"] = fps if fps is not None else config.get("default_fps", 24)
            payload[0]["width"] = width if width is not None else config.get("default_width")
            payload[0]["height"] = height if height is not None else config.get("default_height")

        # Provider settings
        if config.get("provider_settings_key"):
            payload[0]["providerSettings"] = {
                config["provider_settings_key"]: {"cameraFixed": camera_fixed}
            }

        # image_uuid가 있으면 우선 사용 (기존 이미지 UUID)
        if image_uuid is not None:
            payload[0]["frameImages"] = [{"inputImage": image_uuid, "frame": "first"}]
            logger.info(
                f"[Video Task] Mode: Image-to-Video (existing image UUID: {image_uuid})"
            )
        elif image_data is not None:
            payload[0]["frameImages"] = [
                {"inputImage": f"data:image/png;base64,{image_data}", "frame": "first"}
            ]
            logger.info("[Video Task] Mode: Image-to-Video (frameImages included)")
        else:
            # 이미지가 없는 경우: Text-to-Video
            logger.info("[Video Task] Mode: Text-to-Video (no frameImages)")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.info(f"[Video Task] Sending request to {self.base_url}")
            logger.info(f"[Video Task] Payload: {payload}")

            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"[Video Task] API Response: {result}")

                # 에러 체크
                if "errors" in result and len(result["errors"]) > 0:
                    error = result["errors"][0]
                    error_msg = error.get("message", "Unknown error")
                    error_code = error.get("code", "unknown")
                    error_param = error.get("parameter", "unknown")

                    logger.error(
                        f"[Video Task] Runware video generation failed: [{error_code}] {error_msg} (parameter: {error_param})"
                    )
                    logger.error(f"[Video Task] Full error object: {error}")
                    raise Exception(
                        f"Runware API error [{error_code}]: {error_msg} (parameter: {error_param})"
                    )

            except httpx.HTTPStatusError as e:
                # HTTP 에러 발생 시 응답 본문 출력
                error_detail = e.response.text
                logger.error(
                    f"[Video Task] HTTP Status Error: {e.response.status_code}"
                )
                logger.error(f"[Video Task] Error Response Body: {error_detail}")
                raise Exception(f"HTTP {e.response.status_code}: {error_detail}")

        actual_duration = payload[0].get("duration")
        actual_width = payload[0].get("width", "N/A")
        actual_height = payload[0].get("height", "N/A")
        logger.info(
            f"[Video Task] Runware video generation started: model={model}, "
            f"task_uuid={task_uuid}, duration={actual_duration}s, size={actual_width}x{actual_height}"
        )
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
        payload = [{"taskType": "getResponse", "taskUUID": task_id}]

        logger.info(f"[Video Task] Checking status for task_id: {task_id}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"[Video Task] API Response: {result}")

            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(
                    f"[Video Task] HTTP Status Error: {e.response.status_code}"
                )
                logger.error(f"[Video Task] Error Response Body: {error_detail}")
                # 에러 발생 시에도 processing으로 반환 (재시도 허용)
                return {
                    "status": "processing",
                    "progress": 50,
                    "video_url": None,
                    "error": None,
                }
            except Exception as e:
                logger.error(
                    f"[Video Task] Unexpected error: {type(e).__name__}: {str(e)}"
                )
                return {
                    "status": "processing",
                    "progress": 50,
                    "video_url": None,
                    "error": None,
                }

        # Response 파싱 - Runware API는 {"data": [...]} 형태로 응답
        if not result:
            logger.info(f"[Video Task] Empty result, status: processing")
            return {
                "status": "processing",
                "progress": 50,
                "video_url": None,
                "error": None,
            }

        # 에러 체크
        if "errors" in result and len(result["errors"]) > 0:
            error = result["errors"][0]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", "unknown")
            logger.error(f"[Video Task] API returned error: [{error_code}] {error_msg}")
            return {
                "status": "failed",
                "progress": 0,
                "video_url": None,
                "error": f"[{error_code}] {error_msg}",
            }

        # data 배열 확인
        if "data" not in result or len(result["data"]) == 0:
            logger.info(f"[Video Task] No data in result, status: processing")
            return {
                "status": "processing",
                "progress": 50,
                "video_url": None,
                "error": None,
            }

        task_result = result["data"][0]
        logger.info(f"[Video Task] Task result: {task_result}")

        # 완료 체크 - videoURL이 있으면 완료
        if "videoURL" in task_result:
            video_url = task_result["videoURL"]
            logger.info(f"[Video Task] Video completed! URL: {video_url}")
            return {
                "status": "completed",
                "progress": 100,
                "video_url": video_url,
                "error": None,
            }
        # status 필드 체크 (processing 중일 때)
        elif "status" in task_result:
            status = task_result["status"]
            logger.info(f"[Video Task] Task status: {status}")
            if status == "processing":
                return {
                    "status": "processing",
                    "progress": 50,
                    "video_url": None,
                    "error": None,
                }
            elif status == "failed":
                error_msg = task_result.get("error", "Unknown error")
                return {
                    "status": "failed",
                    "progress": 0,
                    "video_url": None,
                    "error": error_msg,
                }
            else:
                # 알 수 없는 상태
                logger.info(f"[Video Task] Unknown status: {status}")
                return {
                    "status": "processing",
                    "progress": 50,
                    "video_url": None,
                    "error": None,
                }
        else:
            # status도 videoURL도 없으면 아직 처리 중
            logger.info(f"[Video Task] No status or videoURL, assuming processing...")
            return {
                "status": "processing",
                "progress": 50,
                "video_url": None,
                "error": None,
            }

    async def download_video(self, video_url: str) -> bytes:
        """
        생성된 비디오 다운로드

        Args:
            video_url: 비디오 URL

        Returns:
            bytes: 비디오 바이너리 데이터
        """
        logger.info(f"[Video Task] Downloading video from {video_url}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            video_size = len(response.content)
            logger.info(
                f"[Video Task] Video downloaded successfully (size: {video_size} bytes)"
            )
            return response.content
