import axios from "axios";
import { logError } from "../utils/errorHandler";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token refresh queue to prevent concurrent refresh calls
let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

// Request Interceptor: Add Authorization header
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

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
      const refreshToken = localStorage.getItem("refresh_token");

      // Auth endpoints should not retry, EXCEPT /auth/logout
      const isAuthEndpoint = originalRequest?.url?.includes("/auth/");

      if (isAuthEndpoint) {
        console.log(
          "⏭️ [REFRESH] Skipping refresh for auth endpoint:",
          originalRequest.url
        );
        return Promise.reject(error);
      }

      if (!refreshToken) {
        // No refresh token, logout
        // console.warn(
        //   "⚠️ [REFRESH] No refresh token found, redirecting to login..."
        // );
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
        return new Promise(() => {});
      }

      // 이미 재발급 진행중인 경우 대기
      if (isRefreshing && refreshPromise) {
        // console.log("⏳ [REFRESH] Already refreshing, waiting...");
        try {
          const newAccessToken = await refreshPromise;
          // console.log("✅ [REFRESH] Got new token from queue, retrying request");
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
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
            { refresh_token: refreshToken },
            {
              headers: {
                "Content-Type": "application/json",
              },
            }
          );

          // console.log("🔄 [REFRESH] Response status:", response.status);
          // console.log("🔄 [REFRESH] Response data:", response.data);

          const { access_token, refresh_token: newRefreshToken } =
            response.data;

          if (!access_token) {
            // console.error("❌ [REFRESH] No access_token in response!");
            throw new Error("No access_token in refresh response");
          }

          localStorage.setItem("access_token", access_token);
          if (newRefreshToken) {
            localStorage.setItem("refresh_token", newRefreshToken);
            // console.log("🔄 [REFRESH] Refresh token rotated");
          }
          // console.log("✅ [REFRESH] Token refreshed successfully");

          return access_token;
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

          // Refresh failed, logout
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
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
        const newAccessToken = await refreshPromise;
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
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
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
      return new Promise(() => {});
    }

    return Promise.reject(error);
  }
);

export default apiClient;
