"""
Word TTS Service
단어 TTS 생성 비즈니스 로직 (Book별 voice_id 지원)
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
from src.tts_generator import TtsGenerator
from core.logging import get_logger

logger = get_logger(__name__)


class WordTTSService:
    """Book별 단어 TTS 생성 서비스"""

    def __init__(self, tts_generator: TtsGenerator):
        self.tts_generator = tts_generator
        self.base_sound_dir = Path("/app/data/sound")
        self.base_book_dir = Path("/app/data/book")

    def validate_word(self, word: str) -> None:
        """
        단어 유효성 검증

        Args:
            word: 검증할 단어

        Raises:
            ValueError: 유효하지 않은 단어
        """
        # 단어 길이 검증 (최대 50자)
        if len(word) > 50:
            raise ValueError("단어 길이는 50자를 초과할 수 없습니다.")

        # 빈 문자열 검증
        if not word.strip():
            raise ValueError("단어는 비어있을 수 없습니다.")

        # 특수문자 검증 (경로 조작 문자 차단)
        if any(char in word for char in [".", "/", "\\", ".."]):
            raise ValueError("단어에 경로 조작 문자(., /, \\)를 포함할 수 없습니다.")

    def load_book_metadata(self, book_id: str) -> Dict[str, Any]:
        """
        Book 메타데이터에서 voice_id 읽기

        Args:
            book_id: Book ID

        Returns:
            Book 메타데이터 (voice_id 포함)

        Raises:
            FileNotFoundError: 메타데이터 파일이 없음
            ValueError: voice_id가 없음
        """
        metadata_path = self.base_book_dir / book_id / "metadata.json"

        if not metadata_path.exists():
            raise FileNotFoundError(f"Book metadata not found: {book_id}")

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        voice_id = metadata.get("voice_id")
        if not voice_id:
            raise ValueError(f"voice_id not found in metadata for book: {book_id}")

        logger.info(f"Loaded metadata for book {book_id}: voice_id={voice_id}")
        return metadata

    def get_word_path(self, book_id: str, word: str) -> Path:
        """
        Book별 단어 파일 경로 생성

        Args:
            book_id: Book ID
            word: 단어

        Returns:
            /app/data/sound/word/{book_id}/{word}.mp3
        """
        return self.base_sound_dir / "word" / book_id / f"{word}.mp3"

    def is_cached(self, book_id: str, word: str) -> bool:
        """
        Book별 캐시된 파일 존재 여부 확인

        Args:
            book_id: Book ID
            word: 단어

        Returns:
            파일 존재 여부
        """
        file_path = self.get_word_path(book_id, word)
        return file_path.exists()

    async def generate_word(self, book_id: str, word: str) -> Dict[str, Any]:
        """
        Book별 단어 TTS 생성 (캐싱 지원)

        Args:
            book_id: Book ID
            word: 변환할 단어

        Returns:
            생성 결과 (word, file_path, cached, duration_ms, voice_id)

        Raises:
            FileNotFoundError: Book 메타데이터가 없음
            ValueError: 유효하지 않은 단어 또는 voice_id 없음
            Exception: TTS 생성 실패 시
        """
        # 유효성 검증
        self.validate_word(word)

        # Book 메타데이터 로드 (voice_id 가져오기)
        metadata = self.load_book_metadata(book_id)
        voice_id = metadata["voice_id"]

        # 캐시 여부 확인
        is_cached = self.is_cached(book_id, word)
        file_path = self.get_word_path(book_id, word)

        logger.info(
            f"단어 TTS 요청: book={book_id}, word='{word}', "
            f"voice_id={voice_id}, cached={is_cached}"
        )

        # 캐시된 파일이 있으면 바로 반환
        if is_cached:
            logger.info(f"캐시된 파일 재사용: {file_path}")
            return {
                "word": word,
                "file_path": str(file_path).removeprefix("/app"),
                "cached": True,
                "duration_ms": None,
                "voice_id": voice_id,
            }

        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # TTS 생성 (voice_id 전달)
        start_time = time.time()

        # TtsGenerator의 generate_word 메서드 호출
        # 기존 메서드가 캐싱을 자체적으로 처리하므로, 직접 파일 경로로 생성하도록 수정 필요
        # 임시로 기존 메서드 사용 후 파일 복사
        try:
            # TtsGenerator에 voice_id와 경로 전달
            await self.tts_generator.generate_word(
                word=word,
                voice_id=voice_id,
                output_path=str(file_path),
            )

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"단어 TTS 생성 완료: book={book_id}, word='{word}', "
                f"경로={file_path}, 처리 시간={duration_ms}ms"
            )

            return {
                "word": word,
                "file_path": str(file_path).removeprefix("/app"),
                "cached": False,
                "duration_ms": duration_ms,
                "voice_id": voice_id,
            }

        except Exception as e:
            logger.error(f"TTS 생성 실패: book={book_id}, word='{word}', error={e}")
            raise
