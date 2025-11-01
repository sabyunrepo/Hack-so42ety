"""
Image Generator Service Module
이미지 생성 (GenAI + 템플릿 복사) 전담 서비스
"""

import shutil
from typing import List, Optional
from pathlib import Path
from io import BytesIO
from fastapi import UploadFile
from google import genai
from google.genai import types

from ..core.config import settings
from ..core.logging import get_logger
from ..prompts.generate_image_prompt import GenerateImagePrompt
from ..storage import AbstractStorageService

logger = get_logger(__name__)


class ImageGeneratorService:
    """이미지 생성 서비스 (GenAI API + 템플릿 복사)"""

    def __init__(
        self,
        storage_service: AbstractStorageService,
        image_data_dir: str,
        genai_client: Optional[genai.Client] = None,
        template_book_id: Optional[str] = None,
        template_image: Optional[str] = None,
    ):
        """
        ImageGeneratorService 초기화

        Args:
            storage_service: 스토리지 서비스 (이미지 업로드용)
            image_data_dir: 이미지 데이터 디렉토리 경로
            genai_client: Google GenAI 클라이언트 (선택적)
            template_book_id: 템플릿 Book ID (테스트용)
            template_image: 템플릿 이미지 파일명 (테스트용)
        """
        self.storage = storage_service
        self.image_data_dir = image_data_dir
        self.genai_client = genai_client
        self.template_book_id = template_book_id or settings.template_book_id
        self.template_image = template_image or settings.template_image

        if genai_client:
            logger.info("ImageGeneratorService initialized with GenAI client")
        else:
            logger.warning("ImageGeneratorService initialized without GenAI client - template mode only")

    async def generate_image_from_template(
        self, index: int, story: List[str], input_img: dict, book_id: str, page_id: str
    ) -> str:
        """
        템플릿 이미지를 복사하여 페이지 이미지 생성 (테스트용)

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열 (미사용)
            input_img: 업로드할 이미지 파일 (미사용)
            book_id: Book ID
            page_id: Page ID

        Returns:
            str: 복사된 이미지 URL
        """
        logger.info(f"[ImageGeneratorService] Copying template image for page {index + 1}")
        try:
            # 템플릿 이미지 경로
            template_path = (
                Path(self.image_data_dir) / self.template_book_id / self.template_image
            )

            # 대상 디렉토리 생성
            target_dir = Path(self.image_data_dir) / book_id
            target_dir.mkdir(parents=True, exist_ok=True)

            # 대상 파일 경로
            target_filename = f"{index}_{page_id}.png"
            target_path = target_dir / target_filename

            # 파일 복사
            shutil.copy2(template_path, target_path)

            # URL 생성
            image_url = f"/data/image/{book_id}/{target_filename}"

            logger.info(f"[ImageGeneratorService] Template image copied: {image_url}")
            return image_url

        except Exception as e:
            logger.error(
                f"[ImageGeneratorService] Template image copy failed for page {index + 1}: {e}",
                exc_info=True,
            )
            return ""

    async def generate_image_with_genai(
        self, index: int, story: List[str], input_img: dict, book_id: str, page_id: str
    ) -> str:
        """
        GenAI API를 호출하여 페이지 이미지 생성 및 업로드

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열
            input_img: 입력 이미지 파일 (dict with 'content' and 'content_type')
            book_id: Book ID
            page_id: Page ID

        Returns:
            str: 업로드된 이미지 URL (실패 시 빈 문자열)
        """
        logger.info(f"[ImageGeneratorService] Generating storybook page image {index + 1}")
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return ""

        try:
            img = types.Part.from_bytes(
                data=input_img["content"], mime_type=input_img["content_type"]
            )
            prompt = GenerateImagePrompt(
                stories=story, style_keyword="cartoon"
            ).render()

            response = await self.genai_client.aio.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(
                        aspect_ratio="3:4",
                    )
                ),
            )

            image_parts = [
                part.inline_data.data
                for part in response.candidates[0].content.parts
                if part.inline_data
            ]

            if image_parts:
                upload_file = UploadFile(
                    file=BytesIO(image_parts[0]),
                    filename=str(index) + "_" + page_id + ".png",
                    headers={"content-type": "image/png"},
                )
                result = await self.storage.upload_image(
                    file=upload_file, book_id=book_id, filename=upload_file.filename
                )
                logger.info(f"[ImageGeneratorService] Image uploaded: {result}")
                return result
            else:
                logger.warning(f"[ImageGeneratorService] No image_parts in GenAI response")
                return ""

        except Exception as e:
            logger.error(
                f"[ImageGeneratorService] Image generation failed for page {index + 1}: {e}",
                exc_info=True,
            )
            return ""
