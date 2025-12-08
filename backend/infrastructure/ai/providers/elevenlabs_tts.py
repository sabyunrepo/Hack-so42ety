"""
ElevenLabs TTS Provider
ElevenLabs API를 사용한 고품질 음성 합성
"""

from typing import Optional, Dict, Any, List
import httpx

from ..base import TTSProvider
from ....core.config import settings
from ....features.tts.exceptions import (
    TTSAPIKeyNotConfiguredException,
    TTSAPIAuthenticationFailedException,
    TTSGenerationFailedException,
)


class ElevenLabsTTSProvider(TTSProvider):
    """
    ElevenLabs TTS Provider

    고품질 음성 합성 서비스
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
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.default_voice_id = settings.tts_default_voice_id
        self.default_model_id = settings.tts_default_model_id
        self.timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """
        텍스트를 음성으로 변환

        Args:
            text: 변환할 텍스트
            voice_id: ElevenLabs 음성 ID
            model_id: ElevenLabs 모델 ID
            language: 언어 코드 (en, ko 등)
            speed: 재생 속도

        Returns:
            bytes: MP3 오디오 데이터
        """
        voice_id = voice_id or self.default_voice_id
        model_id = model_id or self.default_model_id

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={
                        "Accept": "audio/mpeg",
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": model_id,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.0,
                            "use_speaker_boost": True,
                        },
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 오류: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 요청 실패: {str(e)}")

        return response.content

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 음성 목록 조회

        Returns:
            List[Dict[str, Any]]: 음성 정보 리스트
        
        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 API 오류 시
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 오류: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 요청 실패: {str(e)}")

        data = response.json()

        # ElevenLabs 응답 형식을 표준 형식으로 변환
        voices = []
        for voice in data.get("voices", []):
            voices.append(
                {
                    "voice_id": voice["voice_id"],
                    "name": voice["name"],
                    "language": voice.get("labels", {}).get("language", "en"),
                    "gender": voice.get("labels", {}).get("gender", "unknown"),
                    "preview_url": voice.get("preview_url"),
                    "category": voice.get("category", "generated"),
                }
            )

        return voices

    async def get_voice_settings(self, voice_id: str) -> Dict[str, Any]:
        """
        특정 음성의 설정 조회

        Args:
            voice_id: 음성 ID

        Returns:
            Dict[str, Any]: 음성 설정 정보
        
        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 API 오류 시
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/voices/{voice_id}/settings",
                    headers={"xi-api-key": self.api_key},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 오류: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 요청 실패: {str(e)}")

        return response.json()

    async def get_user_info(self) -> Dict[str, Any]:
        """
        사용자 계정 정보 조회 (할당량 등)

        Returns:
            Dict[str, Any]: 사용자 정보
        
        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 API 오류 시
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/user",
                    headers={"xi-api-key": self.api_key},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 오류: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise TTSGenerationFailedException(reason=f"ElevenLabs API 요청 실패: {str(e)}")

        return response.json()
    
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
            Dict[str, Any]: {
                "voice_id": str,
                "name": str,
                "language": str,
                "gender": str,
                "category": str,
                ...
            }
        
        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 API 오류 시
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # multipart/form-data로 파일 업로드
                files = {
                    "files": ("audio.mp3", audio_file, "audio/mpeg"),
                }
                data = {
                    "name": name,
                }
                if description:
                    data["description"] = description
                
                response = await client.post(
                    f"{self.base_url}/voices/add",
                    headers={"xi-api-key": self.api_key},
                    files=files,
                    data=data,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )
            raise TTSGenerationFailedException(
                reason=f"ElevenLabs Voice Clone API 오류: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise TTSGenerationFailedException(
                reason=f"ElevenLabs Voice Clone API 요청 실패: {str(e)}"
            )
        
        data = response.json()
        
        # ElevenLabs 응답 형식을 표준 형식으로 변환
        return {
            "voice_id": data.get("voice_id", ""),
            "name": data.get("name", name),
            "language": data.get("labels", {}).get("language", "en"),
            "gender": data.get("labels", {}).get("gender", "unknown"),
            "category": data.get("category", "cloned"),
            "preview_url": data.get("preview_url"),  # 초기에는 None일 수 있음
            "description": data.get("description", description),
            "labels": data.get("labels", {}),
        }
    
    async def get_voice_details(self, voice_id: str) -> Dict[str, Any]:
        """
        Voice 상세 정보 조회 (상태 포함)
        
        Args:
            voice_id: ElevenLabs Voice ID
        
        Returns:
            Dict[str, Any]: {
                "voice_id": str,
                "name": str,
                "status": str,  # "processing", "completed", "failed"
                "preview_url": Optional[str],
                "language": str,
                "gender": str,
                "category": str,
                ...
            }
        
        Raises:
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 API 오류 시
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/voices/{voice_id}",
                    headers={"xi-api-key": self.api_key},
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TTSAPIAuthenticationFailedException(
                    provider="elevenlabs",
                    reason="API 키가 유효하지 않거나 만료되었습니다"
                )
            if e.response.status_code == 404:
                raise TTSGenerationFailedException(
                    reason=f"Voice를 찾을 수 없습니다: {voice_id}"
                )
            raise TTSGenerationFailedException(
                reason=f"ElevenLabs API 오류: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise TTSGenerationFailedException(
                reason=f"ElevenLabs API 요청 실패: {str(e)}"
            )
        
        data = response.json()
        
        # preview_url이 있으면 완료로 간주
        preview_url = data.get("preview_url")
        status = "completed" if preview_url else "processing"
        
        # ElevenLabs 응답 형식을 표준 형식으로 변환
        return {
            "voice_id": data.get("voice_id", voice_id),
            "name": data.get("name", ""),
            "status": status,
            "preview_url": preview_url,
            "language": data.get("labels", {}).get("language", "en"),
            "gender": data.get("labels", {}).get("gender", "unknown"),
            "category": data.get("category", "generated"),
            "description": data.get("description"),
            "labels": data.get("labels", {}),
        }
