import { useState, useEffect } from "react";
import type { ReactNode } from "react";
import apiClient from "../api/client";
import { AuthContext } from "../contexts/AuthContext"; // 1번에서 만든 객체 가져오기
import type {
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
} from "../types/auth";

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Validate auth status on mount by calling /auth/me
    // Since tokens are stored in httpOnly cookies, we can't check their existence from JavaScript
    // Instead, we call the backend to validate the authentication status
    const validateAuth = async () => {
      try {
        // Call /auth/me to validate the httpOnly cookie-based authentication
        // The access_token cookie will be sent automatically via withCredentials: true
        const response = await apiClient.get<User>("/auth/me");

        // If successful, set user state and sync to localStorage
        setUser(response.data);
        localStorage.setItem("user", JSON.stringify(response.data));
      } catch (error: any) {
        // Handle 401 (unauthenticated) or any other auth failure
        // Clear user state and localStorage
        setUser(null);
        localStorage.removeItem("user");
      } finally {
        setIsLoading(false);
      }
    };

    validateAuth();
  }, []);

  const login = async (data: LoginRequest) => {
    const response = await apiClient.post<AuthResponse>("/auth/login", data);
    const { user } = response.data;

    // Tokens are now set as httpOnly cookies by the backend
    // Only store user info in localStorage for quick access
    localStorage.setItem("user", JSON.stringify(user));
    setUser(user);
  };

  const register = async (data: RegisterRequest) => {
    const response = await apiClient.post<AuthResponse>("/auth/register", data);
    const { user } = response.data;

    // Tokens are now set as httpOnly cookies by the backend
    // Only store user info in localStorage for quick access
    localStorage.setItem("user", JSON.stringify(user));
    setUser(user);
  };

  const googleLogin = async (token: string) => {
    const response = await apiClient.post<AuthResponse>("/auth/google", {
      token,
    });
    const { user } = response.data;

    // Tokens are now set as httpOnly cookies by the backend
    // Only store user info in localStorage for quick access
    localStorage.setItem("user", JSON.stringify(user));
    setUser(user);
  };

  const logout = async () => {
    // Tokens are now stored in httpOnly cookies and sent automatically via withCredentials: true
    // No need to send refresh_token in the body or access_token in headers
    try {
      await apiClient.post("/auth/logout");
    } catch (error) {
      console.error("❌ [LOGOUT] Logout request failed:", error);
    } finally {
      // Clear only user info from localStorage
      // Tokens are cleared by the backend as httpOnly cookies
      localStorage.removeItem("user");
      setUser(null);
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        googleLogin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
