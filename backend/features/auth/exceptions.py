"""
Auth Domain Exceptions
인증 도메인 전용 커스텀 예외
"""

from ...core.exceptions import (
    AuthenticationException,
    ConflictException,
    ErrorCode,
)


class InvalidCredentialsException(AuthenticationException):
    """이메일 또는 비밀번호 불일치"""

    def __init__(self):
        super().__init__(
            error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="이메일 또는 비밀번호가 일치하지 않습니다",
        )


class OAuthUserOnlyException(AuthenticationException):
    """소셜 로그인 전용 사용자"""

    def __init__(self, oauth_provider: str):
        super().__init__(
            error_code=ErrorCode.AUTH_OAUTH_USER_ONLY,
            message=f"소셜 로그인 사용자입니다. {oauth_provider} 로그인을 이용해주세요",
            details={"oauth_provider": oauth_provider},
        )


class EmailAlreadyExistsException(ConflictException):
    """이메일 중복"""

    def __init__(self, email: str):
        super().__init__(
            error_code=ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
            message="이미 사용 중인 이메일입니다",
            details={"email": email},
        )


class InvalidGoogleTokenException(AuthenticationException):
    """Google 토큰 검증 실패"""

    def __init__(self):
        super().__init__(
            error_code=ErrorCode.AUTH_GOOGLE_TOKEN_INVALID,
            message="Google 로그인에 실패했습니다. 다시 시도해주세요",
        )


class InvalidRefreshTokenException(AuthenticationException):
    """Refresh Token 검증 실패"""

    def __init__(self):
        super().__init__(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="유효하지 않은 Refresh Token입니다",
        )
