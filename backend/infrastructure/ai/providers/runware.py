"""
Runware Video Provider
Runware API를 사용한 비디오 생성
"""

import uuid
import base64
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal
import httpx

from ..base import VideoGenerationProvider, ImageGenerationProvider
from ..utils import detect_and_validate_image
from ....core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# 작업 상태 응답 데이터클래스
# ============================================================


@dataclass
class TaskStatusResponse:
    """
    Runware 비동기 작업 상태 응답 표준화

    check_image_status()와 check_video_status()의 공통 반환 타입
    """

    status: Literal["pending", "processing", "completed", "failed"]
    progress: int
    result_url: Optional[str] = None  # imageURL 또는 videoURL
    result_uuid: Optional[str] = None  # imageUUID (이미지 전용)
    error: Optional[str] = None

# ============================================================
# 모델 설정 딕셔너리
# ============================================================

IMAGE_MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "google": {
        "default_width": 896,
        "default_height": 1152,
        "reference_key": "inputs.referenceImages",  # 중첩 구조 (API 요구사항)
        "provider_settings": None,
        "output_type": ["dataURI", "URL"],
        "output_format": "WEBP",
        "include_cost": True,
        "output_quality": 85,
    },
    "google:4@1": {  # Google Imagen 3 (명시적 설정)
        "default_width": 896,
        "default_height": 1152,
        "reference_key": "inputs.referenceImages",  # 중첩 구조
        "provider_settings": None,
        "output_type": ["dataURI", "URL"],
        "output_format": "WEBP",
        "include_cost": True,
        "output_quality": 85,
    },
    "openai:1@2": {  # GPT Image 1 Mini
        "default_width": 1024,
        "default_height": 1024,
        "reference_key": "inputs.referenceImages",  # 중첩 구조
        "provider_settings": {"openai": {"quality": "auto", "background": "opaque"}},
        "output_type": ["dataURI", "URL"],
        "output_format": "WEBP",
        "include_cost": True,
        "output_quality": 85,
    },
    "openai:4@1": {  # GPT Image 1.5
        "default_width": 1024,
        "default_height": 1536,
        "reference_key": "inputs.referenceImages",
        "provider_settings": {"openai": {"quality": "low", "background": "opaque"}},
        "output_type": ["dataURI", "URL"],
        "output_format": "WEBP",
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
    """
    모델 ID에서 이미지 설정 조회 (부분 매칭 지원)

    Args:
        model_id: 모델 식별자 (예: "google:4@1", "openai:1@2")

    Returns:
        Dict[str, Any]: 모델별 설정 딕셔너리
    """
    # 정확한 매칭 우선
    if model_id in IMAGE_MODEL_CONFIGS:
        return IMAGE_MODEL_CONFIGS[model_id]

    # 부분 매칭 (모델 ID에 키가 포함된 경우)
    for key in IMAGE_MODEL_CONFIGS:
        if key in model_id:
            return IMAGE_MODEL_CONFIGS[key]

    # 기본값: google 설정 반환
    return IMAGE_MODEL_CONFIGS["google"]


def get_video_config(model_id: str) -> Dict[str, Any]:
    """
    모델 ID에서 비디오 설정 조회 (부분 매칭 지원)

    Args:
        model_id: 모델 식별자 (예: "klingai:6@0", "bytedance:2@2")

    Returns:
        Dict[str, Any]: 모델별 설정 딕셔너리
    """
    for key in VIDEO_MODEL_CONFIGS:
        if key in model_id:
            return VIDEO_MODEL_CONFIGS[key]
    # 기본값: klingai 설정 반환
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
        # 하위 호환성을 위해 미사용 파라미터 유지
        _ = (strength, cfg_scale, steps, style, quality, background)

        task_uuid = str(uuid.uuid4())
        logger.info(f"[Image Task] Processing input image for Runware API...")
        processed_image, mime_type = detect_and_validate_image(image_data)
        image_base64 = base64.b64encode(processed_image).decode("utf-8")
        logger.info(
            f"[Image Task] Image prepared: mime_type={mime_type}, "
            f"base64_length={len(image_base64)}"
        )
        result = None

        model = settings.runware_img2img_model
        config = get_image_config(model)

        # 기본 페이로드 (공통 필드) - 항상 비동기 모드 사용
        payload = [
            {
                "taskType": "imageInference",
                "taskUUID": task_uuid,
                "positivePrompt": prompt,
                "model": model,
                "numberResults": 1,
                "deliveryMethod": "async",  # 타임아웃 방지를 위한 비동기 모드
            }
        ]

        # 모델 설정 기반 크기 적용
        payload[0]["width"] = width if width is not None else config["default_width"]
        payload[0]["height"] = height if height is not None else config["default_height"]

        # 참조 이미지 설정 (모델별 중첩/최상위 구조)
        if config["reference_key"] == "inputs.referenceImages":
            payload[0]["inputs"] = {
                "referenceImages": [f"data:{mime_type};base64,{image_base64}"]
            }
            logger.info(
                f"[Image Task] Applied referenceImage to inputs.referenceImages "
                f"with data:{mime_type};base64,..."
            )
        else:
            payload[0]["referenceImages"] = [f"data:{mime_type};base64,{image_base64}"]
            logger.info(
                f"[Image Task] Applied referenceImage to referenceImages "
                f"with data:{mime_type};base64,..."
            )

        # 프로바이더별 설정
        if config.get("provider_settings"):
            payload[0]["providerSettings"] = config["provider_settings"]

        # 선택적 출력 설정 (OpenAI 전용)
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

            # HTTP 에러 처리
            if response.status_code >= 400:
                logger.error("[Image Task] Runware API 에러 발생")
                logger.error(f"[Image Task] 상태 코드: {response.status_code}")
                logger.error(f"[Image Task] 응답 텍스트: {response.text}")
                try:
                    error_json = response.json()
                    logger.error(f"[Image Task] 응답 JSON: {error_json}")
                except Exception:
                    logger.error("[Image Task] 응답이 JSON 형식이 아님")
                response.raise_for_status()

            result = response.json()

            # 응답 내 API 에러 확인
            if "error" in result:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"[Image Task] Runware 이미지 생성 실패: {error_msg}")
                raise Exception(f"Runware API error: {error_msg}")

            # errors 배열 확인 (Runware 에러 형식)
            if "errors" in result and len(result["errors"]) > 0:
                error = result["errors"][0]
                error_msg = error.get("message", "Unknown error")
                error_code = error.get("code", "unknown")
                logger.error(f"[Image Task] Runware API 에러: [{error_code}] {error_msg}")
                raise Exception(f"Runware API error [{error_code}]: {error_msg}")

            # 비동기 모드: 폴링을 위한 task_uuid 반환
            actual_width = payload[0].get("width")
            actual_height = payload[0].get("height")

            logger.info(
                f"[Image Task] Async request submitted: task_uuid={task_uuid}, "
                f"model={model}, size={actual_width}x{actual_height}"
            )

            return {"task_uuid": task_uuid}

    # ========== 작업 상태 확인 (통합 메서드) ==========

    async def _check_task_status(
        self,
        task_id: str,
        task_type: Literal["image", "video"],
    ) -> TaskStatusResponse:
        """
        Runware 비동기 작업 상태 확인 (공통 로직)

        이미지와 비디오 작업의 상태 확인 로직을 통합한 내부 메서드.
        check_image_status()와 check_video_status()에서 래퍼로 호출됨.

        Args:
            task_id: Runware task UUID
            task_type: "image" 또는 "video"

        Returns:
            TaskStatusResponse: 표준화된 작업 상태 응답

        상태 매핑 (Runware API → 내부 상태):
            - imageURL/videoURL 있음 -> "completed"
            - status="processing" -> "processing"
            - status="success" (URL 없음) -> "processing" (대기)
            - status="error" -> "failed"
            - errors 배열 있음 -> "failed"
            - 빈 응답/데이터 없음 -> "processing"
        """
        # 타입별 설정
        url_key = "imageURL" if task_type == "image" else "videoURL"
        uuid_key = "imageUUID" if task_type == "image" else None
        log_tag = f"[{task_type.capitalize()} Task]"

        payload = [{"taskType": "getResponse", "taskUUID": task_id}]
        logger.info(f"{log_tag} 상태 확인: task_id={task_id[:8]}...")

        # ========== API 호출 ==========
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

            except httpx.HTTPStatusError as e:
                logger.warning(f"{log_tag} HTTP 에러 (재시도): {e.response.status_code}")
                return TaskStatusResponse(status="processing", progress=50)

            except Exception as e:
                logger.warning(f"{log_tag} 예외 (재시도): {type(e).__name__}")
                return TaskStatusResponse(status="processing", progress=50)

        # ========== 응답 파싱 ==========
        if not result:
            return TaskStatusResponse(status="processing", progress=50)

        # errors 배열 확인 (Runware 에러 형식)
        if "errors" in result and result["errors"]:
            err = result["errors"][0]
            error_msg = f"[{err.get('code', 'unknown')}] {err.get('message', 'Unknown')}"
            logger.error(f"{log_tag} ❌ API 에러: {error_msg}")
            return TaskStatusResponse(status="failed", progress=0, error=error_msg)

        # data 배열 확인
        if "data" not in result or not result["data"]:
            return TaskStatusResponse(status="processing", progress=50)

        task_result = result["data"][0]

        # ========== 완료 확인 (타입별 URL 키 사용) ==========
        if url_key in task_result:
            result_url = task_result[url_key]
            result_uuid = task_result.get(uuid_key) if uuid_key else None
            # URL 로깅 (이미지는 길어서 truncate)
            log_url = result_url[:80] + "..." if len(result_url) > 80 else result_url
            logger.info(f"{log_tag} ✅ 완료! URL: {log_url}")
            return TaskStatusResponse(
                status="completed",
                progress=100,
                result_url=result_url,
                result_uuid=result_uuid,
            )

        # ========== status 필드 분기 ==========
        # Runware API 상태값: "processing", "success", "error"
        if "status" in task_result:
            status = task_result["status"]
            logger.info(f"{log_tag} 작업 상태: {status}")

            if status == "processing":
                return TaskStatusResponse(status="processing", progress=50)

            elif status == "success":
                # URL 없이 success (엣지 케이스)
                return TaskStatusResponse(
                    status="processing",
                    progress=80,
                    result_uuid=task_result.get(uuid_key) if uuid_key else None,
                )

            elif status == "error":
                error_msg = task_result.get(
                    "message", task_result.get("error", "Unknown error")
                )
                logger.error(f"{log_tag} ❌ 실패: {error_msg}")
                return TaskStatusResponse(status="failed", progress=0, error=error_msg)

        # 기본값: 처리 중
        return TaskStatusResponse(status="processing", progress=50)

    # ========== 이미지 상태 확인 (래퍼) ==========

    async def check_image_status(self, task_id: str) -> Dict[str, Any]:
        """
        비동기 이미지 생성 상태 확인

        Args:
            task_id: generate_image_from_image()에서 반환된 Runware task UUID

        Returns:
            Dict[str, Any]: {
                "status": str,      # "pending", "processing", "completed", "failed"
                "progress": int,    # 0-100
                "image_url": Optional[str],
                "image_uuid": Optional[str],
                "error": Optional[str]
            }
        """
        result = await self._check_task_status(task_id, "image")
        return {
            "status": result.status,
            "progress": result.progress,
            "image_url": result.result_url,
            "image_uuid": result.result_uuid,
            "error": result.error,
        }

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
        # 파라미터 검증
        if duration is not None and not (1.2 <= duration <= 12):
            raise ValueError(
                f"duration은 1.2~12초 사이여야 합니다. 입력값: {duration}"
            )

        if output_quality < 20 or output_quality > 99:
            raise ValueError(
                f"output_quality는 20~99 사이여야 합니다. 입력값: {output_quality}"
            )

        task_uuid = str(uuid.uuid4())
        model = settings.runware_video_model
        config = get_video_config(model)

        # 기본 페이로드 (공통 필드)
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

        # 모델 설정 기반 값 적용
        payload[0]["duration"] = duration if duration is not None else config["default_duration"]

        # 크기 설정 (지원 모델만)
        if config.get("supports_dimensions"):
            payload[0]["fps"] = fps if fps is not None else config.get("default_fps", 24)
            payload[0]["width"] = width if width is not None else config.get("default_width")
            payload[0]["height"] = height if height is not None else config.get("default_height")

        # 프로바이더별 설정
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
            logger.info("[Video Task] Processing input image for video generation...")
            processed_image, mime_type = detect_and_validate_image(image_data)
            encoded = base64.b64encode(processed_image).decode("utf-8")
            logger.info(
                f"[Video Task] Image prepared: mime_type={mime_type}, "
                f"base64_length={len(encoded)}"
            )
            payload[0]["frameImages"] = [
                {"inputImage": f"data:{mime_type};base64,{encoded}", "frame": "first"}
            ]
            logger.info(
                f"[Video Task] Applied frameImages with data:{mime_type};base64,..."
            )
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

    # ========== 비디오 상태 확인 (래퍼) ==========

    async def check_video_status(self, task_id: str) -> Dict[str, Any]:
        """
        비디오 생성 상태 확인

        Args:
            task_id: generate_video()에서 반환된 Runware task UUID

        Returns:
            Dict[str, Any]: {
                "status": str,  # pending, processing, completed, failed
                "progress": int,  # 0~100
                "video_url": Optional[str],
                "error": Optional[str]
            }
        """
        result = await self._check_task_status(task_id, "video")
        return {
            "status": result.status,
            "progress": result.progress,
            "video_url": result.result_url,
            "error": result.error,
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
