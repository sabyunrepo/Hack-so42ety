"""
TTS Domain Exceptions
TTS 도메인 전용 커스텀 예외
"""

from ...core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessLogicException,
    ErrorCode,
)


class TTSGenerationFailedException(BusinessLogicException):
    """음성 생성 실패"""

    def __init__(self, reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_TTS_GENERATION_FAILED,
            message="음성 생성에 실패했습니다",
            details={"reason": reason} if reason else None,
        )


class TTSUploadFailedException(BusinessLogicException):
    """음성 파일 업로드 실패"""

    def __init__(self, filename: str = None, reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_TTS_UPLOAD_FAILED,
            message="음성 파일 업로드에 실패했습니다",
            details={"filename": filename, "reason": reason} if filename or reason else None,
        )


class TTSTextTooLongException(ValidationException):
    """텍스트가 너무 김"""

    def __init__(self, text_length: int, max_length: int = 5000):
        super().__init__(
            error_code=ErrorCode.BIZ_TTS_TEXT_TOO_LONG,
            message=f"텍스트가 너무 깁니다 (최대 {max_length}자)",
            details={"text_length": text_length, "max_length": max_length},
        )


class TTSVoiceNotFoundException(NotFoundException):
    """요청하신 음성을 찾을 수 없음"""

    def __init__(self, voice_id: str):
        super().__init__(
            error_code=ErrorCode.BIZ_TTS_VOICE_NOT_FOUND,
            message="요청하신 음성을 찾을 수 없습니다",
            details={"voice_id": voice_id},
        )


class TTSAPIKeyNotConfiguredException(BusinessLogicException):
    """TTS API 키가 설정되지 않음"""

    def __init__(self, provider: str = "elevenlabs"):
        super().__init__(
            error_code=ErrorCode.BIZ_TTS_API_KEY_NOT_CONFIGURED,
            message=f"{provider} API 키가 설정되지 않았습니다. 환경 변수를 확인해주세요.",
            details={"provider": provider, "env_var": "ELEVENLABS_API_KEY"},
        )


class TTSAPIAuthenticationFailedException(BusinessLogicException):
    """TTS API 인증 실패"""

    def __init__(self, provider: str = "elevenlabs", reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_TTS_API_AUTHENTICATION_FAILED,
            message=f"{provider} API 인증에 실패했습니다. API 키를 확인해주세요.",
            details={"provider": provider, "reason": reason} if reason else {"provider": provider},
        )
