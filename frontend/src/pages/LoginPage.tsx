import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
// import { GoogleLogin } from "@react-oauth/google";
import { getUserFriendlyErrorMessage } from "../utils/errorHandler";
import { usePostHog } from "@posthog/react";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();
  const posthog = usePostHog();

  // 이메일 형식 검증
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) {
      setEmailError("이메일을 입력해주세요");
      return false;
    }
    if (!emailRegex.test(email)) {
      setEmailError("올바른 이메일 형식이 아닙니다");
      return false;
    }
    setEmailError("");
    return true;
  };

  // 비밀번호 형식 검증
  const validatePassword = (password: string): boolean => {
    if (!password) {
      setPasswordError("비밀번호를 입력해주세요");
      return false;
    }
    if (password.length < 8) {
      setPasswordError("비밀번호는 최소 8자 이상이어야 합니다");
      return false;
    }
    // [ ] 비밀번호 형식 확인 후 개선
    // if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
    //   setPasswordError("비밀번호는 영문 대소문자와 숫자를 포함해야 합니다");
    //   return false;
    // }
    setPasswordError("");
    return true;
  };

  const handleEmailBlur = () => {
    if (email) {
      validateEmail(email);
    }
  };

  const handlePasswordBlur = () => {
    if (password) {
      validatePassword(password);
    }
  };

const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // ✅ 폼 제출 시 이전 에러를 초기화 (필수)
    setError("");

    // 폼 제출 시 전체 검증
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);

    if (!isEmailValid || !isPasswordValid) {
      return;
    }


    try {
      await login({ email, password });
      posthog?.capture("login_success", { method: "email" });
      navigate("/");
    } catch (err) {


      setError(getUserFriendlyErrorMessage(err));

    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-linear-to-br from-orange-50 via-amber-50/50 to-orange-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-md rounded-2xl bg-white/80 backdrop-blur-sm p-6 sm:p-8 shadow-2xl border border-amber-100">
        <div className="text-center mb-8">
          {/* <div className="text-5xl mb-4">📚</div> */}
          <h2 className="text-3xl font-bold bg-gradient-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
            로그인
          </h2>
          <p className="text-amber-700 mt-2 text-sm">
            동화책 세상으로 들어가보세요!
          </p>
        </div>

        {/* {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="text-lg">⚠️</span>
              <span>{error}</span>
            </div>
          </div>
        )} */}

{error && (
  <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 shadow-sm">
    <div className="flex items-start gap-2">
      <span className="text-lg flex-shrink-0">⚠️</span>
      <span className="flex-1 text-sm leading-snug">{error}</span>
      <button
        onClick={() => setError("")}
        className="ml-4 p-0.5 text-red-700 hover:text-red-900 transition-colors flex-shrink-0"
        aria-label="닫기"
      >
        &times;
      </button>
    </div>
  </div>
)}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              className="mb-2 block text-sm font-bold text-amber-900"
              htmlFor="email"
            >
              이메일
            </label>
            <input
              className={`w-full appearance-none rounded-lg border-2 px-4 py-3 leading-tight text-gray-700 bg-white/50 focus:outline-none focus:bg-white transition-all duration-200 shadow-sm ${
                emailError
                  ? "border-red-400 focus:border-red-500"
                  : "border-amber-200 focus:border-amber-400"
              }`}
              id="email"
              type="email"
              placeholder="example@email.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError("");
              }}
              onBlur={handleEmailBlur}
              required
            />
            {emailError && (
              <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                <span>⚠️</span>
                <span>{emailError}</span>
              </p>
            )}
          </div>
          <div>
            <label
              className="mb-2 block text-sm font-bold text-amber-900"
              htmlFor="password"
            >
              비밀번호
            </label>
            <input
              className={`w-full appearance-none rounded-lg border-2 px-4 py-3 leading-tight text-gray-700 bg-white/50 focus:outline-none focus:bg-white transition-all duration-200 shadow-sm ${
                passwordError
                  ? "border-red-400 focus:border-red-500"
                  : "border-amber-200 focus:border-amber-400"
              }`}
              id="password"
              type="password"
              placeholder="비밀번호를 입력하세요"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (passwordError) setPasswordError("");
              }}
              onBlur={handlePasswordBlur}
              required
            />
            {passwordError && (
              <p className="mt-2 text-sm text-red-600 flex items-center gap-1">
                <span>⚠️</span>
                <span>{passwordError}</span>
              </p>
            )}
            {/* <p className="mt-2 text-xs text-amber-600">
              * 8자 이상, 영문 대소문자와 숫자 포함
            </p> */}
          </div>
          <div className="pt-4">
            <button
              className="w-full bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold px-6 py-3 rounded-full shadow-lg hover:shadow-xl hover:from-amber-500 hover:to-amber-600 focus:outline-none focus:ring-4 focus:ring-amber-300 transition-all duration-300 transform hover:scale-[1.02] active:scale-95"
              type="submit"
            >
              로그인하기
            </button>
          </div>
          <div className="text-center pt-4">
            {/* [ ] 회원가입 주석처리 */}
            {/* <p className="text-sm text-amber-700">
              아직 계정이 없으신가요?{" "}
              <Link
                className="font-bold text-amber-600 hover:text-amber-800 underline decoration-2 decoration-amber-300 hover:decoration-amber-500 transition-colors"
                to="/register"
              >
                회원가입
              </Link>
            </p> */}
          </div>
          {/* [ ] 소셜로그인 추후 개선 */}
          {/*
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-2 text-gray-500">Or continue with</span>
              </div>
            </div>

            <div className="mt-6 flex justify-center">
              <div className="w-full">
                <GoogleLogin
                  onSuccess={async (credentialResponse) => {
                    if (credentialResponse.credential) {
                      try {
                        await googleLogin(credentialResponse.credential);
                        navigate("/");
                      } catch (err) {
                        console.error("Google login error:", err);
                        setError(getUserFriendlyErrorMessage(err));
                      }
                    }
                  }}
                  onError={() => {
                    console.error("Google OAuth 403 - 테스트 사용자 설정을 확인하세요");
                    setError("Google 로그인 오류: OAuth 동의 화면에서 테스트 사용자를 추가해주세요");
                  }}
                  useOneTap={false}
                  theme="outline"
                  size="large"
                  text="continue_with"
                  width="100%"
                />
              </div>
            </div>
          </div> */}
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
