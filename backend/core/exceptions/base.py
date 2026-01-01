"""
Base Exception Classes
기본 예외 클래스
"""

from typing import Optional, Dict, Any
from fastapi import status


class AppException(Exception):
    """
    애플리케이션 기본 예외

    모든 커스텀 예외의 베이스 클래스
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            error_code: 에러 코드 (예: AUTH_001)
            message: 사용자 친화적 에러 메시지
            status_code: HTTP 상태 코드
            details: 추가 에러 정보 (선택사항)
        """
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"error_code={self.error_code!r}, "
            f"message={self.message!r}, "
            f"status_code={self.status_code})"
        )


class AuthenticationException(AppException):
    """
    인증 실패 예외 (401 Unauthorized)

    사용자 인증에 실패한 경우 발생
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationException(AppException):
    """
    권한 부족 예외 (403 Forbidden)

    인증은 되었으나 권한이 부족한 경우 발생
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ValidationException(AppException):
    """
    검증 실패 예외 (400 Bad Request)

    요청 데이터 검증에 실패한 경우 발생
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundException(AppException):
    """
    리소스 없음 예외 (404 Not Found)

    요청한 리소스를 찾을 수 없는 경우 발생
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictException(AppException):
    """
    충돌 예외 (409 Conflict)

    리소스 상태 충돌이 발생한 경우 (예: 중복 생성)
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class BusinessLogicException(AppException):
    """
    비즈니스 로직 예외 (400 Bad Request)

    비즈니스 규칙 위반 시 발생
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class InternalServerException(AppException):
    """
    서버 내부 오류 예외 (500 Internal Server Error)

    예상치 못한 서버 오류 발생 시
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class RateLimitExceededException(AppException):
    """
    속도 제한 초과 예외 (429 Too Many Requests)

    요청 속도 제한을 초과한 경우 발생
    """

    def __init__(
        self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )
