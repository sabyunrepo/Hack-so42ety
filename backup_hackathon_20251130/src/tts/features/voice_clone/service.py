"""
Voice Clone Service
클론 보이스 생성 비즈니스 로직 (TtsGenerator 위임)
"""

from pathlib import Path
from typing import Optional
from fastapi import UploadFile
from src.tts_generator import TtsGenerator
from core.logging import get_logger

logger = get_logger(__name__)


class VoiceCloneService:
    """클론 보이스 생성 서비스 (얇은 레이어)"""

    ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB

    def __init__(self, tts_generator: TtsGenerator):
        self.tts_generator = tts_generator

    def _validate_file(self, file: UploadFile) -> None:
        """
        파일 기본 검증 (확장자, 크기)

        Args:
            file: 업로드된 파일

        Raises:
            ValueError: 검증 실패
        """
        # 확장자 검증
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"지원하지 않는 파일 형식입니다. "
                f"허용 형식: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )

        # 파일 크기 검증
        if hasattr(file, "size") and file.size:
            if file.size > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"파일 크기가 너무 큽니다. "
                    f"최대 크기: {self.MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
                )

    async def _save_temp_file(self, file: UploadFile) -> Path:
        """
        임시 파일 저장

        Args:
            file: 업로드된 파일

        Returns:
            Path: 저장된 파일 경로
        """
        temp_path = self.tts_generator.temp_dir / file.filename

        try:
            content = await file.read()

            # 실제 크기 검증
            if len(content) > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"파일 크기가 너무 큽니다. "
                    f"최대 크기: {self.MAX_FILE_SIZE / (1024 * 1024):.0f}MB"
                )

            with open(temp_path, "wb") as f:
                f.write(content)

            logger.info(f"임시 파일 저장: {temp_path}")
            return temp_path

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def validate_audio_before_background(
        self, name: str, file: UploadFile
    ) -> Path:
        """
        백그라운드 처리 전 동기 검증

        Args:
            name: 보이스 이름
            file: 오디오 파일

        Returns:
            Path: 검증 완료된 임시 파일 경로

        Raises:
            ValueError: 검증 실패
        """
        temp_file_path: Optional[Path] = None

        try:
            # 1. 파일 기본 검증 (확장자, 크기)
            self._validate_file(file)
            logger.info(f"파일 검증 완료: {file.filename}")

            # 2. 중복 이름 확인
            if await self.tts_generator.check_duplicate_voice_name(name):
                raise ValueError(f"'{name}' 이름이 이미 존재합니다. 다른 이름을 사용하세요.")

            # 3. 임시 파일 저장
            temp_file_path = await self._save_temp_file(file)

            # 4. 오디오 길이만 검증 (트리밍은 백그라운드에서)
            duration = self.tts_generator.validate_audio_duration_only(temp_file_path)
            logger.info(f"오디오 길이 검증 완료: {duration:.2f}초")

            return temp_file_path

        except ValueError:
            # 검증 실패 시 임시 파일 삭제
            if temp_file_path:
                self.tts_generator._cleanup_temp_file(temp_file_path)
            raise

        except Exception as e:
            # 예상치 못한 에러 시 임시 파일 삭제
            if temp_file_path:
                self.tts_generator._cleanup_temp_file(temp_file_path)
            logger.error(f"오디오 검증 실패: {str(e)}")
            raise ValueError(f"오디오 파일 검증 중 오류가 발생했습니다: {str(e)}")

    async def create_clone_voice_from_path(
        self, name: str, temp_file_path: Path, description: str = ""
    ) -> dict:
        """
        이미 저장된 파일로 클론 보이스 생성 (백그라운드용)

        Args:
            name: 보이스 이름
            temp_file_path: 임시 파일 경로 (이미 검증 완료)
            description: 보이스 설명

        Returns:
            dict: 생성된 보이스 정보

        Raises:
            ValueError: API 오류
        """
        try:
            # TtsGenerator에 클론 생성 위임 (오디오 검증 + 트리밍 + API 호출)
            result = await self.tts_generator.create_clone_voice(
                name=name.strip(),
                audio_file_path=temp_file_path,
                description=description.strip(),
            )

            # 성공 시 임시 파일 삭제
            self.tts_generator._cleanup_temp_file(temp_file_path)

            return result

        except Exception as e:
            # 실패 시 임시 파일 삭제
            self.tts_generator._cleanup_temp_file(temp_file_path)
            logger.error(f"클론 보이스 생성 실패: {str(e)}")
            raise ValueError(f"클론 보이스 생성 중 오류가 발생했습니다: {str(e)}")

    async def create_clone_voice(
        self, name: str, file: UploadFile, description: str = ""
    ) -> dict:
        """
        클론 보이스 생성 (컨트롤러 계층 위임)

        Args:
            name: 보이스 이름
            file: 오디오 파일
            description: 보이스 설명

        Returns:
            dict: 생성된 보이스 정보

        Raises:
            ValueError: 검증 실패, 중복 이름, API 오류
        """
        temp_file_path: Optional[Path] = None

        try:
            # 1. 파일 기본 검증
            self._validate_file(file)
            logger.info(f"파일 검증 완료: {file.filename}")

            # 2. 중복 이름 확인 (TtsGenerator 위임)
            if await self.tts_generator.check_duplicate_voice_name(name):
                raise ValueError(f"'{name}' 이름이 이미 존재합니다. 다른 이름을 사용하세요.")

            # 3. 임시 파일 저장
            temp_file_path = await self._save_temp_file(file)

            # 4. TtsGenerator에 클론 생성 위임 (오디오 검증, 트리밍, API 호출 포함)
            result = await self.tts_generator.create_clone_voice(
                name=name.strip(),
                audio_file_path=temp_file_path,
                description=description.strip(),
            )

            # 5. 성공 시 임시 파일 삭제
            self.tts_generator._cleanup_temp_file(temp_file_path)

            return result

        except ValueError:
            # Validation 에러 - 임시 파일 삭제
            if temp_file_path:
                self.tts_generator._cleanup_temp_file(temp_file_path)
            raise

        except Exception as e:
            # 예상치 못한 에러 - 임시 파일 삭제
            if temp_file_path:
                self.tts_generator._cleanup_temp_file(temp_file_path)

            logger.error(f"클론 보이스 생성 실패: {str(e)}")
            raise ValueError(f"클론 보이스 생성 중 오류가 발생했습니다: {str(e)}")
