"""
TTS Service Module
TTS API 연동 및 오디오 파일 생성 전담 서비스
"""

from typing import List, Optional
import httpx

from ..core.logging import get_logger

logger = get_logger(__name__)


class TtsService:
    """TTS API 호출 및 오디오 생성 서비스"""

    def __init__(self, tts_api_url: str, http_client: httpx.AsyncClient):
        """
        TtsService 초기화

        Args:
            tts_api_url: TTS API 서버 URL
            http_client: 재사용 가능한 HTTP 클라이언트 인스턴스
        """
        self.tts_api_url = tts_api_url
        self.http_client = http_client
        logger.info(f"TtsService initialized - TTS API: {tts_api_url}")

    async def generate_tts_audio(self, dialogs: List[List[str]], voice_id: str) -> List[List[Optional[str]]]:
        """
        TTS API 호출하여 오디오 파일 생성

        Args:
            dialogs: 2차원 배열 [[페이지1 대사1, 대사2], [페이지2 대사1], ...]
            voice_id: TTS 음성 ID

        Returns:
            List[List[Optional[str]]]: 생성된 오디오 파일 URL 2차원 배열 (실패 시 None)
        """

        if not dialogs:
            logger.warning("[TtsService] Empty dialogs list for TTS generation")
            return []

        try:
            logger.info(
                f"[TtsService] Calling TTS API: {self.tts_api_url}/tts/dialog/generate with voice_id: {voice_id}"
            )
            logger.debug(f"[TtsService] TTS request data: {dialogs}")

            # TTS API 호출 (비동기)
            # 타임아웃: 페이지당 10초 + 기본 30초 (최소 120초)
            timeout_seconds = max(120.0, len(dialogs) * 10.0)

            # 재사용 가능한 클라이언트 사용 + 요청별 타임아웃 오버라이드
            response = await self.http_client.post(
                f"{self.tts_api_url}/tts/dialog/generate",
                json={"texts": dialogs, "voice_id": voice_id},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            result = response.json()

            logger.debug(f"[TtsService] TTS API raw response: {result}")

            # 결과에서 오디오 URL 추출
            # TTS API 응답: {"paths": [["/path/to/audio1.mp3"], ["/path/to/audio2.mp3"]], ...}
            paths = result.get("paths", [])

            if not paths:
                logger.error("[TtsService] TTS API returned empty paths")
                return [[None] * len(page_dialogs) for page_dialogs in dialogs]

            # TTS API 응답 구조: {"paths": [[url1, url2], [url3, url4]], ...} (2차원 배열)
            # paths는 이미 dialogs와 동일한 2차원 구조로 반환됨
            audio_urls = []

            for page_idx, page_paths in enumerate(paths):
                page_urls = []

                # page_paths가 리스트인지 확인
                if isinstance(page_paths, list):
                    for dialog_idx, audio_url in enumerate(page_paths):
                        if audio_url:
                            # /app 접두사 제거 (컨테이너 내부 경로 → 외부 접근 경로)
                            cleaned_url = (
                                audio_url.removeprefix("/app")
                                if isinstance(audio_url, str)
                                else audio_url
                            )
                            page_urls.append(cleaned_url)
                            logger.debug(
                                f"[TtsService] Page {page_idx + 1}, Dialog {dialog_idx + 1}: {cleaned_url}"
                            )
                        else:
                            page_urls.append(None)
                            logger.warning(
                                f"[TtsService] Page {page_idx + 1}, Dialog {dialog_idx + 1}: No audio URL"
                            )
                else:
                    # 예상치 못한 형식
                    logger.error(
                        f"[TtsService] Unexpected path format for page {page_idx + 1}: {type(page_paths)}"
                    )
                    page_urls = (
                        [None] * len(dialogs[page_idx])
                        if page_idx < len(dialogs)
                        else []
                    )

                audio_urls.append(page_urls)

            # 페이지 수 검증
            if len(audio_urls) != len(dialogs):
                logger.warning(
                    f"[TtsService] TTS API page count mismatch: "
                    f"expected {len(dialogs)}, got {len(audio_urls)}"
                )
                # 부족한 페이지 추가
                while len(audio_urls) < len(dialogs):
                    audio_urls.append([None] * len(dialogs[len(audio_urls)]))

            # 각 페이지의 대사 수 검증 및 조정
            for page_idx, (expected_dialogs, actual_urls) in enumerate(
                zip(dialogs, audio_urls)
            ):
                if len(actual_urls) != len(expected_dialogs):
                    logger.warning(
                        f"[TtsService] Page {page_idx + 1} dialog count mismatch: "
                        f"expected {len(expected_dialogs)}, got {len(actual_urls)}"
                    )
                    # 부족한 만큼 None 추가
                    while len(actual_urls) < len(expected_dialogs):
                        actual_urls.append(None)
                    # 초과분 제거
                    if len(actual_urls) > len(expected_dialogs):
                        audio_urls[page_idx] = actual_urls[: len(expected_dialogs)]

            # 총 성공한 URL 개수 계산
            success_count = sum(
                1 for page_urls in audio_urls for url in page_urls if url
            )
            total_expected = sum(len(page_dialogs) for page_dialogs in dialogs)

            logger.info(
                f"[TtsService] TTS API returned {success_count}/{total_expected} audio files across {len(audio_urls)} pages"
            )

            return audio_urls

        except httpx.TimeoutException as e:
            logger.error(f"[TtsService] TTS API timeout after {timeout_seconds}s: {e}")
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[TtsService] TTS API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
        except httpx.RequestError as e:
            logger.error(f"[TtsService] TTS API connection error: {e}")
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
        except Exception as e:
            logger.error(f"[TtsService] TTS API unexpected error: {e}", exc_info=True)
            return [[None] * len(page_dialogs) for page_dialogs in dialogs]
