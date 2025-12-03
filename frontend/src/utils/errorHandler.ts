/**
 * Error Handler Utility
 * 에러 처리 유틸리티
 */

import { AxiosError } from 'axios';
import type { BackendError, ValidationError } from '../types/error';

/**
 * Type guard for AxiosError
 */
function isAxiosError(error: unknown): error is AxiosError {
  return (error as AxiosError).isAxiosError === true;
}

/**
 * Axios 에러에서 백엔드 에러 추출
 *
 * @param error - Unknown error object
 * @returns BackendError if valid backend error, null otherwise
 */
export const extractBackendError = (error: unknown): BackendError | null => {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data;
    // 백엔드 표준 에러 형식 확인
    if (
      data &&
      typeof data === 'object' &&
      'error_code' in data &&
      'message' in data &&
      'status_code' in data
    ) {
      return data as BackendError;
    }
  }
  return null;
};

/**
 * Axios 에러에서 Validation 에러 추출
 *
 * @param error - Unknown error object
 * @returns ValidationError if valid validation error, null otherwise
 */
export const extractValidationError = (error: unknown): ValidationError | null => {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data;
    if (data && typeof data === 'object' && 'errors' in data && Array.isArray(data.errors)) {
      return data as ValidationError;
    }
  }
  return null;
};

/**
 * 사용자 친화적 에러 메시지 생성
 *
 * 우선순위:
 * 1. 백엔드 표준 에러의 message 필드
 * 2. Axios 에러별 기본 메시지
 * 3. 일반 에러 메시지
 *
 * @param error - Unknown error object
 * @returns User-friendly error message
 */
export const getUserFriendlyErrorMessage = (error: unknown): string => {
  // 1. 백엔드 표준 에러 메시지 우선
  const backendError = extractBackendError(error);
  if (backendError) {
    return backendError.message;
  }

  // 2. Validation 에러 처리
  const validationError = extractValidationError(error);
  if (validationError && validationError.errors.length > 0) {
    // 첫 번째 validation 에러 메시지 반환
    return validationError.errors[0].message;
  }

  // 3. Axios 에러 기본 처리
  if (isAxiosError(error)) {
    // 타임아웃
    if (error.code === 'ECONNABORTED') {
      return '요청 시간이 초과되었습니다. 다시 시도해주세요.';
    }

    // 네트워크 에러
    if (!error.response) {
      return '서버와 연결할 수 없습니다. 네트워크를 확인해주세요.';
    }

    // HTTP 상태 코드별 기본 메시지
    const status = error.response.status;
    switch (status) {
      case 400:
        return '잘못된 요청입니다.';
      case 401:
        return '인증이 필요합니다. 다시 로그인해주세요.';
      case 403:
        return '접근 권한이 없습니다.';
      case 404:
        return '요청하신 리소스를 찾을 수 없습니다.';
      case 500:
        return '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      case 503:
        return '서비스를 일시적으로 사용할 수 없습니다.';
      default:
        return `오류가 발생했습니다. (${status})`;
    }
  }

  // 4. 기본 에러 메시지
  if (error instanceof Error) {
    return error.message || '예상치 못한 오류가 발생했습니다.';
  }

  return '예상치 못한 오류가 발생했습니다.';
};

/**
 * 에러 코드별 특수 처리가 필요한지 확인
 *
 * @param errorCode - Error code from backend
 * @returns true if detailed error should be shown
 */
export const shouldShowDetailedError = (errorCode: string): boolean => {
  // 개발 환경에서만 시스템 에러 상세 표시
  return import.meta.env.DEV && errorCode.startsWith('SYS_');
};

/**
 * 에러 로깅 (개발 환경용)
 *
 * @param error - Error object
 * @param context - Additional context
 */
export const logError = (error: unknown, context?: string): void => {
  if (!import.meta.env.DEBUG) return;

  const backendError = extractBackendError(error);

  if (backendError) {
    console.error(
      `[${backendError.error_code}] ${backendError.message}`,
      {
        context,
        path: backendError.path,
        request_id: backendError.request_id,
        details: backendError.details,
        timestamp: backendError.timestamp,
      }
    );
  } else {
    console.error('Error:', error, { context });
  }
};
