/**
 * Backend Error Response Types
 * 백엔드 에러 응답 타입 정의
 */

/**
 * 백엔드 표준 에러 응답 형식
 */
export interface BackendError {
  error_code: string;        // "AUTH_001", "BIZ_001" 등
  message: string;           // 한글 사용자 메시지
  status_code: number;       // HTTP 상태 코드
  timestamp: string;         // ISO 8601 형식
  request_id: string;        // UUID
  path: string;              // API 경로
  details?: Record<string, any> | null;  // 추가 상세 정보
}

/**
 * Validation Error 응답 형식
 */
export interface ValidationError {
  error_code: string;
  message: string;
  status_code: number;
  timestamp: string;
  request_id: string;
  path: string;
  errors: Array<{
    field: string;
    message: string;
    type: string;
  }>;
}

/**
 * 에러 카테고리 (에러 코드 prefix 기반)
 */
export const ErrorCategory = {
  AUTHENTICATION: 'AUTH',
  AUTHORIZATION: 'AUTHZ',
  VALIDATION: 'VAL',
  BUSINESS: 'BIZ',
  SYSTEM: 'SYS',
  NOT_FOUND: 'NF',
} as const;

export type ErrorCategoryType = typeof ErrorCategory[keyof typeof ErrorCategory];

/**
 * 에러 코드 추출
 */
export const getErrorCategory = (errorCode: string): ErrorCategoryType | null => {
  const prefix = errorCode.split('_')[0];
  const categories = Object.values(ErrorCategory);
  return categories.includes(prefix as ErrorCategoryType)
    ? (prefix as ErrorCategoryType)
    : null;
};
