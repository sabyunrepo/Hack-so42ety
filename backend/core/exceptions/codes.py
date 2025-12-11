"""
Error Code Definitions
에러 코드 정의
"""

from enum import Enum


class ErrorCode(str, Enum):
    """
    애플리케이션 에러 코드

    규칙:
    - AUTH_xxx: 인증 관련 에러 (401)
    - AUTHZ_xxx: 권한 관련 에러 (403)
    - VAL_xxx: 검증 관련 에러 (400, 422)
    - BIZ_xxx: 비즈니스 로직 에러 (400, 404, 409)
    - SYS_xxx: 시스템 에러 (500)
    """

    # ==================== Authentication (AUTH_xxx) ====================
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    """이메일 또는 비밀번호가 일치하지 않습니다"""

    AUTH_OAUTH_USER_ONLY = "AUTH_002"
    """OAuth 전용 사용자 (소셜 로그인 필수)"""

    AUTH_TOKEN_EXPIRED = "AUTH_003"
    """토큰이 만료되었습니다"""

    AUTH_TOKEN_INVALID = "AUTH_004"
    """유효하지 않은 토큰입니다"""

    AUTH_EMAIL_ALREADY_EXISTS = "AUTH_005"
    """이미 등록된 이메일입니다"""

    AUTH_GOOGLE_TOKEN_INVALID = "AUTH_006"
    """Google 토큰 검증에 실패했습니다"""

    # ==================== Authorization (AUTHZ_xxx) ====================
    AUTHZ_FORBIDDEN = "AUTHZ_001"
    """접근 권한이 없습니다"""

    AUTHZ_INSUFFICIENT_PERMISSIONS = "AUTHZ_002"
    """권한이 부족합니다"""

    # ==================== Validation (VAL_xxx) ====================
    VAL_INVALID_INPUT = "VAL_001"
    """입력 데이터가 유효하지 않습니다"""

    VAL_MISSING_FIELD = "VAL_002"
    """필수 필드가 누락되었습니다"""

    VAL_INVALID_FORMAT = "VAL_003"
    """잘못된 형식입니다"""

    # ==================== Business Logic (BIZ_xxx) ====================
    BIZ_RESOURCE_NOT_FOUND = "BIZ_001"
    """리소스를 찾을 수 없습니다"""

    BIZ_OPERATION_FAILED = "BIZ_002"
    """작업 수행에 실패했습니다"""

    BIZ_DUPLICATE_RESOURCE = "BIZ_003"
    """중복된 리소스입니다"""

    BIZ_BOOK_NOT_FOUND = "BIZ_101"
    """동화책을 찾을 수 없습니다"""

    BIZ_BOOK_CREATION_FAILED = "BIZ_102"
    """동화책 생성에 실패했습니다"""

    BIZ_BOOK_UNAUTHORIZED = "BIZ_103"
    """동화책 접근 권한이 없습니다"""

    BIZ_BOOK_IMAGE_UPLOAD_FAILED = "BIZ_104"
    """이미지 업로드에 실패했습니다"""

    BIZ_BOOK_STORIES_IMAGES_MISMATCH = "BIZ_105"
    """스토리와 이미지 개수가 일치하지 않습니다"""

    BIZ_BOOK_AI_GENERATION_FAILED = "BIZ_106"
    """AI 생성에 실패했습니다"""

    BIZ_BOOK_INVALID_PAGE_COUNT = "BIZ_107"
    """잘못된 페이지 수입니다"""

    BIZ_BOOK_QUOTA_EXCEEDED = "BIZ_108"
    """책 생성 한도를 초과했습니다"""

    BIZ_TTS_GENERATION_FAILED = "BIZ_201"
    """음성 생성에 실패했습니다"""

    BIZ_TTS_UPLOAD_FAILED = "BIZ_202"
    """음성 파일 업로드에 실패했습니다"""

    BIZ_TTS_TEXT_TOO_LONG = "BIZ_203"
    """텍스트가 너무 깁니다"""

    BIZ_TTS_VOICE_NOT_FOUND = "BIZ_204"
    """요청하신 음성을 찾을 수 없습니다"""

    BIZ_TTS_API_KEY_NOT_CONFIGURED = "BIZ_205"
    """TTS API 키가 설정되지 않았습니다"""

    BIZ_TTS_API_AUTHENTICATION_FAILED = "BIZ_206"
    """TTS API 인증에 실패했습니다"""

    # ==================== System (SYS_xxx) ====================
    SYS_INTERNAL_ERROR = "SYS_001"
    """서버 내부 오류가 발생했습니다"""

    SYS_DATABASE_ERROR = "SYS_002"
    """데이터베이스 오류가 발생했습니다"""

    SYS_EXTERNAL_SERVICE_ERROR = "SYS_003"
    """외부 서비스 연동 중 오류가 발생했습니다"""
