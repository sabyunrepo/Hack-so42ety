import axios from "axios";
import { logError } from "../utils/errorHandler";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Enable sending httpOnly cookies with requests
});

// Token refresh queue to prevent concurrent refresh calls
let isRefreshing = false;
let refreshPromise: Promise<void> | null = null;

// Response Interceptor: Handle 401 and Token Refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 개발 환경에서 백엔드 에러 로깅
    logError(error, `API Request: ${originalRequest?.url}`);

    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Auth endpoints should not retry, EXCEPT /auth/logout
      const isAuthEndpoint =
        originalRequest?.url?.includes("/auth/") &&
        !originalRequest?.url?.includes("/auth/logout");

      if (isAuthEndpoint) {
        console.log(
          "⏭️ [REFRESH] Skipping refresh for auth endpoint:",
          originalRequest.url
        );
        return Promise.reject(error);
      }

      // 이미 재발급 진행중인 경우 대기
      if (isRefreshing && refreshPromise) {
        // console.log("⏳ [REFRESH] Already refreshing, waiting...");
        try {
          await refreshPromise;
          // console.log("✅ [REFRESH] Got new token from queue, retrying request");
          return apiClient(originalRequest);
        } catch (err) {
          return Promise.reject(err);
        }
      }

      // 재발급 로직  시작
      isRefreshing = true;
      // console.log("🔄 [REFRESH] Starting token refresh...");

      refreshPromise = (async () => {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/auth/refresh`,
            {}, // Empty body - refresh_token sent as httpOnly cookie
            {
              headers: {
                "Content-Type": "application/json",
              },
              withCredentials: true, // Send cookies with request
            }
          );

          // console.log("🔄 [REFRESH] Response status:", response.status);
          // console.log("🔄 [REFRESH] Response data:", response.data);
          // console.log("✅ [REFRESH] Token refreshed successfully (cookies updated by backend)");
        } catch (refreshError) {
          // console.error("❌ [REFRESH] Token refresh failed:", refreshError);

          // Log detailed error information
          if (axios.isAxiosError(refreshError)) {
            console.error(
              "❌ [REFRESH] Status:",
              refreshError.response?.status
            );
            console.error(
              "❌ [REFRESH] Response:",
              refreshError.response?.data
            );
          }

          // Refresh failed, logout (cookies will be cleared by backend)
          localStorage.removeItem("user");

          console.warn("🚪 [REFRESH] Redirecting to login...");
          window.location.href = "/login";

          throw refreshError;
        } finally {
          isRefreshing = false;
          refreshPromise = null;
        }
      })();

      try {
        await refreshPromise;
        console.log(
          "🔄 [REFRESH] Retrying original request to:",
          originalRequest.url
        );
        return apiClient(originalRequest);
      } catch (_err) {
        // Return a promise that never resolves to prevent error propagation during redirect
        // 리디렉션 중 오류 전파를 방지하기 위해 절대 해결되지 않는 프로미스를 반환
        console.log(_err);
        return new Promise(() => {});
      }
    }

    // If we reach here, either:
    // 1. Status is not 401
    // 2. Already tried refreshing (_retry = true)
    if (error.response?.status === 401 && originalRequest._retry) {
      console.error("❌ [INTERCEPTOR] 401 after refresh attempt, logging out");
      localStorage.removeItem("user");
      window.location.href = "/login";
      return new Promise(() => {});
    }

    return Promise.reject(error);
  }
);

export default apiClient;
