"""
Audio Processor Utility
오디오 파일 처리 유틸리티 (상태 없음)
"""

import logging
from pathlib import Path
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioProcessor:
    """오디오 처리 유틸리티 클래스 (상태 없음)"""

    @staticmethod
    def get_duration(file_path: Path) -> float:
        """
        오디오 파일 길이 조회

        Args:
            file_path: 오디오 파일 경로

        Returns:
            float: 오디오 길이 (초)

        Raises:
            ValueError: 유효하지 않은 오디오 파일
        """
        try:
            audio = AudioSegment.from_file(str(file_path))
            duration_seconds = len(audio) / 1000.0
            logger.info(f"오디오 길이: {duration_seconds:.2f}초")
            return duration_seconds
        except Exception as e:
            logger.error(f"오디오 파일 {file_path} 길이 분석 실패: {e}")
            raise ValueError(f"유효하지 않은 오디오 파일입니다: {e}")

    @staticmethod
    def trim_audio(file_path: Path, target_duration: float) -> Path:
        """
        오디오 파일 트리밍

        Args:
            file_path: 원본 파일 경로
            target_duration: 목표 길이 (초)

        Returns:
            Path: 트리밍된 파일 경로

        Raises:
            ValueError: 트리밍 실패
        """
        try:
            audio = AudioSegment.from_file(str(file_path))
            target_ms = int(target_duration * 1000)
            trimmed_audio = audio[:target_ms]

            trimmed_path = file_path.with_name(f"trimmed_{file_path.name}")
            trimmed_audio.export(str(trimmed_path), format=file_path.suffix[1:])

            logger.info(f"오디오 트리밍 완료: {target_duration}초")
            return trimmed_path
        except Exception as e:
            logger.error(f"오디오 트리밍 실패: {e}")
            raise ValueError(f"오디오 트리밍 중 오류 발생: {e}")

    @staticmethod
    def validate_duration(file_path: Path, min_duration: int) -> float:
        """
        오디오 길이 검증 (최소 길이 체크)

        Args:
            file_path: 오디오 파일 경로
            min_duration: 최소 길이 (초)

        Returns:
            float: 오디오 길이 (초)

        Raises:
            ValueError: 길이 부족
        """
        duration = AudioProcessor.get_duration(file_path)

        if duration < min_duration:
            raise ValueError(
                f"오디오 길이가 너무 짧습니다. "
                f"최소 {min_duration // 60}분 {min_duration % 60}초 필요 "
                f"(현재: {int(duration // 60)}분 {int(duration % 60)}초)"
            )

        return duration
