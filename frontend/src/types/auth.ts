export interface User {
  id: string;
  email: string;
}

export interface AuthResponse {
  user: User;
  // Tokens are now stored in httpOnly cookies and not included in response body
  // access_token and refresh_token removed for XSS protection
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}
