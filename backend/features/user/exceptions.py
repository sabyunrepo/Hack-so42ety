"""
User Domain Exceptions
사용자 도메인 전용 커스텀 예외
"""

from ...core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessLogicException,
    ErrorCode,
)


class UserNotFoundException(NotFoundException):
    """사용자를 찾을 수 없음"""

    def __init__(self, user_id: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
            message="사용자를 찾을 수 없습니다",
            details={"user_id": user_id} if user_id else None,
        )


class UserUpdateFailedException(BusinessLogicException):
    """사용자 정보 수정 실패"""

    def __init__(self, reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_OPERATION_FAILED,
            message="사용자 정보 수정에 실패했습니다",
            details={"reason": reason} if reason else None,
        )


class InvalidPasswordException(ValidationException):
    """유효하지 않은 비밀번호"""

    def __init__(self, reason: str = None):
        super().__init__(
            error_code=ErrorCode.VAL_INVALID_INPUT,
            message="비밀번호가 유효하지 않습니다",
            details={"reason": reason} if reason else None,
        )

