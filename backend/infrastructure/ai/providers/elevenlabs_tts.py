"""
ElevenLabs TTS Provider (SDK-based)
ElevenLabs Python SDK를 사용한 고품질 음성 합성
"""

from typing import Optional, Dict, Any, List
import logging

from elevenlabs.client import ElevenLabs
from elevenlabs.types import PronunciationDictionaryVersionLocator

from ..base import TTSProvider
from ....core.config import settings
from ....features.tts.exceptions import (
    TTSAPIKeyNotConfiguredException,
    TTSAPIAuthenticationFailedException,
    TTSGenerationFailedException,
)

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """
    ElevenLabs TTS Provider (SDK-based)

    고품질 음성 합성 서비스 with automatic optimization:
    - Smart model selection (eleven_flash_v2 for single characters)
    - Automatic pronunciation dictionary application for alphabet letters
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: ElevenLabs API Key (None일 경우 settings에서 가져옴)

        Raises:
            TTSAPIKeyNotConfiguredException: API 키가 설정되지 않은 경우
        """
        self.api_key = api_key or settings.elevenlabs_api_key
        if not self.api_key:
            raise TTSAPIKeyNotConfiguredException(provider="elevenlabs")

        # Initialize SDK client
        self.client = ElevenLabs(api_key=self.api_key)

        # Default settings
        self.default_voice_id = settings.tts_default_voice_id
        self.default_model_id = settings.tts_default_model_id

        # Pronunciation dictionary settings
        self.pronunciation_dict_id = settings.pronunciation_dictionary_id
        self.pronunciation_version_id = settings.pronunciation_version_id

    def _select_model_for_text(self, text: str, model_id: Optional[str]) -> str:
        """
        Smart model selection based on text characteristics

        Args:
            text: Input text
            model_id: User-specified model (takes precedence)

        Returns:
            str: Selected model ID
        """
        if model_id:
            return model_id  # User override

        # Single alphabet character → use ultra-fast model
        if len(text.strip()) == 1 and text.strip().isalpha():
            return "eleven_flash_v2"

        # General text → use default model
        return self.default_model_id

    def _should_use_pronunciation_dict(self, text: str) -> bool:
        """
        Determine if pronunciation dictionary should be applied

        Args:
            text: Input text

        Returns:
            bool: True if pronunciation dictionary should be used
        """
        if not self.pronunciation_dict_id or not self.pronunciation_version_id:
            return False

        # Apply pronunciation dictionary only for single alphabet characters
        return len(text.strip()) == 1 and text.strip().isalpha()

    def _get_pronunciation_locators(self) -> Optional[List[PronunciationDictionaryVersionLocator]]:
        """
        Create pronunciation dictionary locators

        Returns:
            Optional[List[PronunciationDictionaryVersionLocator]]: Locators or None
        """
        if self.pronunciation_dict_id and self.pronunciation_version_id:
            return [PronunciationDictionaryVersionLocator(
                pronunciation_dictionary_id=self.pronunciation_dict_id,
                version_id=self.pronunciation_version_id
            )]
        return None

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """
        텍스트를 음성으로 변환 (automatic optimization)

        Args:
            text: 변환할 텍스트
            voice_id: ElevenLabs 음성 ID
            model_id: ElevenLabs 모델 ID (None이면 자동 선택)
            language: 언어 코드 (en, ko 등)
            speed: 재생 속도

        Returns:
            bytes: MP3 오디오 데이터

        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패
            TTSGenerationFailedException: TTS 생성 실패
        """
        # Smart model selection
        selected_model = self._select_model_for_text(text, model_id)

        # Determine if pronunciation dictionary should be used
        use_pronunciation = self._should_use_pronunciation_dict(text)
        pronunciation_locators = self._get_pronunciation_locators() if use_pronunciation else None

        # Log optimization decisions
        logger.info(
            f"TTS Request: text='{text[:20]}...', model={selected_model}, "
            f"use_pronunciation_dict={use_pronunciation}"
        )

        try:
            # Generate audio using SDK
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id or self.default_voice_id,
                text=text,
                model_id=selected_model,
                pronunciation_dictionary_locators=pronunciation_locators,
            )

            # Collect audio bytes
            audio_bytes = b"".join(audio_generator)

            logger.info(f"TTS Success: {len(audio_bytes)} bytes generated")
            return audio_bytes

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"ElevenLabs TTS SDK Error: text='{text[:50]}...', "
                f"model={selected_model}, error={error_msg}"
            )

            # Check for authentication errors
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason=f"API 키가 유효하지 않거나 만료되었습니다: {error_msg}"
                )

            # Check for voice not found errors
            if "404" in error_msg or "not found" in error_msg.lower():
                raise TTSGenerationFailedException(
                    reason=f"Voice ID '{voice_id or self.default_voice_id}'를 찾을 수 없습니다: {error_msg}"
                )

            # Generic error
            raise TTSGenerationFailedException(
                reason=f"ElevenLabs TTS 생성 실패: {error_msg}"
            )

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 음성 목록 조회

        Returns:
            List[Dict[str, Any]]: 음성 정보 리스트

        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패
            TTSGenerationFailedException: API 오류
        """
        try:
            # Get voices using SDK
            voices_response = self.client.voices.get_all()

            # Convert to standard format
            voices = []
            for voice in voices_response.voices:
                voices.append({
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "language": getattr(voice.labels, "language", "en") if hasattr(voice, "labels") else "en",
                    "gender": getattr(voice.labels, "gender", "unknown") if hasattr(voice, "labels") else "unknown",
                    "preview_url": voice.preview_url if hasattr(voice, "preview_url") else None,
                    "category": voice.category if hasattr(voice, "category") else "generated",
                })

            return voices

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ElevenLabs get_available_voices error: {error_msg}")

            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )

            raise TTSGenerationFailedException(
                reason=f"음성 목록 조회 실패: {error_msg}"
            )

    async def get_voice_settings(self, voice_id: str) -> Dict[str, Any]:
        """
        특정 음성의 설정 조회

        Args:
            voice_id: 음성 ID

        Returns:
            Dict[str, Any]: 음성 설정 정보

        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패
            TTSGenerationFailedException: API 오류
        """
        try:
            # Get voice settings using SDK
            settings_response = self.client.voices.get_settings(voice_id=voice_id)

            # Convert to dictionary
            return {
                "stability": settings_response.stability,
                "similarity_boost": settings_response.similarity_boost,
                "style": getattr(settings_response, "style", 0.0),
                "use_speaker_boost": getattr(settings_response, "use_speaker_boost", True),
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ElevenLabs get_voice_settings error: voice_id={voice_id}, error={error_msg}")

            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )

            raise TTSGenerationFailedException(
                reason=f"음성 설정 조회 실패: {error_msg}"
            )

    async def get_user_info(self) -> Dict[str, Any]:
        """
        사용자 계정 정보 조회 (할당량 등)

        Returns:
            Dict[str, Any]: 사용자 정보

        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패
            TTSGenerationFailedException: API 오류
        """
        try:
            # Get user info using SDK
            user_response = self.client.user.get()

            # Convert to dictionary
            return {
                "subscription": {
                    "tier": user_response.subscription.tier if hasattr(user_response, "subscription") else "free",
                    "character_count": getattr(user_response.subscription, "character_count", 0) if hasattr(user_response, "subscription") else 0,
                    "character_limit": getattr(user_response.subscription, "character_limit", 0) if hasattr(user_response, "subscription") else 0,
                }
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ElevenLabs get_user_info error: {error_msg}")

            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )

            raise TTSGenerationFailedException(
                reason=f"사용자 정보 조회 실패: {error_msg}"
            )

    async def clone_voice(
        self,
        name: str,
        audio_file: bytes,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Voice Clone 생성

        Args:
            name: Voice 이름
            audio_file: 오디오 파일 (bytes)
            description: Voice 설명 (선택)

        Returns:
            Dict[str, Any]: 생성된 voice 정보

        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패
            TTSGenerationFailedException: Voice clone 실패
        """
        try:
            # Note: SDK's voice cloning API requires file-like object
            # This is a simplified implementation - may need adjustment based on actual SDK API
            from io import BytesIO

            audio_file_obj = BytesIO(audio_file)
            audio_file_obj.name = "audio.mp3"

            # Clone voice using SDK
            voice_response = self.client.voices.clone(
                name=name,
                files=[audio_file_obj],
                description=description,
            )

            # Convert to standard format
            return {
                "voice_id": voice_response.voice_id,
                "name": voice_response.name,
                "language": getattr(voice_response.labels, "language", "en") if hasattr(voice_response, "labels") else "en",
                "gender": getattr(voice_response.labels, "gender", "unknown") if hasattr(voice_response, "labels") else "unknown",
                "category": "cloned",
                "preview_url": voice_response.preview_url if hasattr(voice_response, "preview_url") else None,
                "description": description,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ElevenLabs clone_voice error: name={name}, error={error_msg}")

            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )

            raise TTSGenerationFailedException(
                reason=f"Voice Clone 생성 실패: {error_msg}"
            )

    async def get_voice_details(self, voice_id: str) -> Dict[str, Any]:
        """
        Voice 상세 정보 조회 (상태 포함)

        Args:
            voice_id: ElevenLabs Voice ID

        Returns:
            Dict[str, Any]: Voice 상세 정보

        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패
            TTSGenerationFailedException: Voice 조회 실패
        """
        try:
            # Get voice details using SDK
            voice_response = self.client.voices.get(voice_id=voice_id)

            # Determine status based on preview_url availability
            preview_url = voice_response.preview_url if hasattr(voice_response, "preview_url") else None
            status = "completed" if preview_url else "processing"

            # Convert to standard format
            return {
                "voice_id": voice_response.voice_id,
                "name": voice_response.name,
                "status": status,
                "preview_url": preview_url,
                "language": getattr(voice_response.labels, "language", "en") if hasattr(voice_response, "labels") else "en",
                "gender": getattr(voice_response.labels, "gender", "unknown") if hasattr(voice_response, "labels") else "unknown",
                "category": voice_response.category if hasattr(voice_response, "category") else "generated",
                "description": voice_response.description if hasattr(voice_response, "description") else None,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"ElevenLabs get_voice_details error: voice_id={voice_id}, error={error_msg}")

            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )

            if "404" in error_msg or "not found" in error_msg.lower():
                raise TTSGenerationFailedException(
                    reason=f"Voice를 찾을 수 없습니다: {voice_id}"
                )

            raise TTSGenerationFailedException(
                reason=f"Voice 상세 정보 조회 실패: {error_msg}"
            )
