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
    // Check for existing token and user data
    const token = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");

    if (token && storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (data: LoginRequest) => {
    const response = await apiClient.post<AuthResponse>("/auth/login", data);
    const { user, access_token, refresh_token } = response.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(user));
    setUser(user);
  };

  const register = async (data: RegisterRequest) => {
    const response = await apiClient.post<AuthResponse>("/auth/register", data);
    const { user, access_token, refresh_token } = response.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(user));
    setUser(user);
  };

  const googleLogin = async (token: string) => {
    const response = await apiClient.post<AuthResponse>("/auth/google", {
      token,
    });
    const { user, access_token, refresh_token } = response.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
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
