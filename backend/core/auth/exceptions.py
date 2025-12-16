"""
Core Authentication Exceptions
핵심 인증 관련 예외
"""

from ..exceptions import AuthenticationException, ErrorCode


class TokenExpiredException(AuthenticationException):
    """토큰 만료"""

    def __init__(self):
        super().__init__(
            error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="토큰이 만료되었습니다",
        )


class InvalidTokenException(AuthenticationException):
    """유효하지 않은 토큰"""

    def __init__(self):
        super().__init__(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="유효하지 않은 토큰입니다",
        )
