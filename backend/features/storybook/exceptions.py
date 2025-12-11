"""
Storybook Domain Exceptions
동화책 도메인 전용 커스텀 예외
"""

from ...core.exceptions import (
    NotFoundException,
    AuthorizationException,
    ValidationException,
    BusinessLogicException,
    ErrorCode,
)


class StorybookNotFoundException(NotFoundException):
    """동화책을 찾을 수 없음"""

    def __init__(self, storybook_id: str):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_NOT_FOUND,
            message="요청하신 동화책을 찾을 수 없습니다",
            details={"storybook_id": storybook_id},
        )


class StorybookUnauthorizedException(AuthorizationException):
    """동화책 접근 권한 없음"""

    def __init__(self, storybook_id: str, user_id: str):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_UNAUTHORIZED,
            message="이 동화책에 접근할 권한이 없습니다",
            details={"storybook_id": storybook_id, "user_id": str(user_id)},
        )


class StorybookCreationFailedException(BusinessLogicException):
    """동화책 생성 실패"""

    def __init__(self, reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_CREATION_FAILED,
            message="동화책 생성에 실패했습니다",
            details={"reason": reason} if reason else None,
        )


class ImageUploadFailedException(BusinessLogicException):
    """이미지 업로드 실패"""

    def __init__(self, filename: str = None, reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_IMAGE_UPLOAD_FAILED,
            message="이미지 업로드에 실패했습니다",
            details={"filename": filename, "reason": reason} if filename or reason else None,
        )


class StoriesImagesMismatchException(ValidationException):
    """스토리와 이미지 개수 불일치"""

    def __init__(self, stories_count: int, images_count: int):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_STORIES_IMAGES_MISMATCH,
            message="스토리와 이미지 개수가 일치하지 않습니다",
            details={"stories_count": stories_count, "images_count": images_count},
        )


class AIGenerationFailedException(BusinessLogicException):
    """AI 생성 실패"""

    def __init__(self, stage: str, reason: str = None):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_AI_GENERATION_FAILED,
            message=f"AI {stage} 생성에 실패했습니다",
            details={"stage": stage, "reason": reason} if reason else {"stage": stage},
        )


class InvalidPageCountException(ValidationException):
    """잘못된 페이지 수"""

    def __init__(self, page_count: int, min_pages: int = 1, max_pages: int = 5):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_INVALID_PAGE_COUNT,
            message=f"페이지 수는 {min_pages}~{max_pages} 사이여야 합니다",
            details={"requested": page_count, "min": min_pages, "max": max_pages},
        )


class BookQuotaExceededException(BusinessLogicException):
    """책 생성 한도 초과"""

    def __init__(self, current_count: int, max_allowed: int, user_id: str):
        super().__init__(
            error_code=ErrorCode.BIZ_BOOK_QUOTA_EXCEEDED,
            message=f"책 생성 한도를 초과했습니다 ({current_count}/{max_allowed}).",
            details={
                "current_count": current_count,
                "max_allowed": max_allowed,
                "user_id": user_id
            },
        )
