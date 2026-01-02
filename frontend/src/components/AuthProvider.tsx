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
    // Check for existing user data in localStorage
    // Tokens are now stored in httpOnly cookies and not accessible via JavaScript
    const storedUser = localStorage.getItem("user");

    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
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
    const refreshToken = localStorage.getItem("refresh_token");

    if (!refreshToken) {
      // Refresh Token이 없으면 로컬 클리어만
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      return;
    }
    try {
      await apiClient.post<AuthResponse>(
        "/auth/logout",
        {
          refresh_token: localStorage.getItem("refresh_token"),
        },
        {
          headers: {
            Authorization: `Bearer${localStorage.getItem("access_token")}`,
          },
        }
      );
    } catch (error) {
      console.error("❌ [LOGOUT] Logout request failed:", error);
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
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
