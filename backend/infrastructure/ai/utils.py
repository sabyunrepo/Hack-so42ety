"""
AI Provider Utilities
이미지 처리 및 MIME 타입 감지 유틸리티
"""

import logging
from io import BytesIO
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Runware API 지원 MIME 타입
SUPPORTED_MIME_TYPES = frozenset({
    "image/png",
    "image/jpeg",
    "image/webp",
})

# Pillow format -> MIME type 매핑
FORMAT_TO_MIME = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
    "TIFF": "image/tiff",
}

# 미지원 형식 변환 대상
CONVERSION_TARGET = "WEBP"
CONVERSION_MIME = "image/webp"


class InvalidImageDataError(Exception):
    """잘못된 이미지 데이터 예외"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid image data: {reason}")


def detect_and_validate_image(image_bytes: bytes) -> Tuple[bytes, str]:
    """
    이미지 감지, 검증, 필요시 WEBP로 변환

    Runware API가 지원하는 형식(PNG, JPEG, WEBP)이면 원본 반환.
    지원하지 않는 형식(GIF, BMP 등)이면 WEBP로 변환하여 반환.

    Args:
        image_bytes: 원본 이미지 바이너리

    Returns:
        Tuple[bytes, str]: (처리된 이미지 바이트, MIME 타입)

    Raises:
        InvalidImageDataError: 잘못된 이미지 데이터
    """
    if not image_bytes or len(image_bytes) < 8:
        logger.error("[Image Task] Image data is empty or too small")
        raise InvalidImageDataError("Image data is empty or too small")

    original_size = len(image_bytes)
    logger.info(f"[Image Task] Detecting MIME type for image ({original_size} bytes)")

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            format_name = img.format
            if not format_name:
                logger.error("[Image Task] Could not determine image format")
                raise InvalidImageDataError("Could not determine image format")

            mime_type = FORMAT_TO_MIME.get(format_name, f"image/{format_name.lower()}")
            img_size = img.size  # (width, height)

            logger.info(
                f"[Image Task] Detected format: {format_name} ({mime_type}), "
                f"size: {img_size[0]}x{img_size[1]}, mode: {img.mode}"
            )

            # 지원하는 포맷이면 그대로 반환
            if mime_type in SUPPORTED_MIME_TYPES:
                logger.info(
                    f"[Image Task] ✅ Supported format, using original: "
                    f"{format_name} ({mime_type}), {original_size} bytes"
                )
                return image_bytes, mime_type

            # 미지원 형식 → WEBP 변환
            logger.warning(
                f"[Image Task] ⚠️ Unsupported format detected: {format_name} ({mime_type})"
            )
            logger.info(
                f"[Image Task] Converting {format_name} -> {CONVERSION_TARGET}..."
            )
            output = BytesIO()

            # RGBA/팔레트 모드 처리 (GIF 투명도 등)
            original_mode = img.mode
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                logger.info(f"[Image Task] Converted mode: {original_mode} -> RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")
                logger.info(f"[Image Task] Converted mode: {original_mode} -> RGB")

            img.save(output, format=CONVERSION_TARGET, quality=85)
            converted_bytes = output.getvalue()
            converted_size = len(converted_bytes)

            size_diff = original_size - converted_size
            size_pct = (size_diff / original_size * 100) if original_size > 0 else 0

            logger.info(
                f"[Image Task] ✅ Conversion complete: {format_name} -> {CONVERSION_TARGET}, "
                f"{original_size} -> {converted_size} bytes "
                f"({size_pct:+.1f}% size change)"
            )

            return converted_bytes, CONVERSION_MIME

    except InvalidImageDataError:
        raise
    except Exception as e:
        logger.error(f"[Image Task] ❌ Failed to process image: {type(e).__name__}: {e}")
        raise InvalidImageDataError(f"Failed to process image: {type(e).__name__}: {e}")
