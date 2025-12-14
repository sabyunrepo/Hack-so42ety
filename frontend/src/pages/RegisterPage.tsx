import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import { getUserFriendlyErrorMessage } from "../utils/errorHandler";

const RegisterPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState("");
  const { register } = useAuth();
  const navigate = useNavigate();

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
    setPasswordError("");
    return true;
  };

  // 비밀번호 확인 검증
  const validateConfirmPassword = (confirmPw: string): boolean => {
    if (!confirmPw) {
      setConfirmPasswordError("비밀번호 확인을 입력해주세요");
      return false;
    }
    if (password !== confirmPw) {
      setConfirmPasswordError("비밀번호가 일치하지 않습니다");
      return false;
    }
    setConfirmPasswordError("");
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

  const handleConfirmPasswordBlur = () => {
    if (confirmPassword) {
      validateConfirmPassword(confirmPassword);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // 폼 제출 시 전체 검증
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);
    const isConfirmPasswordValid = validateConfirmPassword(confirmPassword);

    if (!isEmailValid || !isPasswordValid || !isConfirmPasswordValid) {
      return;
    }

    try {
      await register({ email, password });
      navigate("/");
    } catch (err) {
      setError(getUserFriendlyErrorMessage(err));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-linear-to-br from-orange-50 via-amber-50/50 to-orange-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="w-full max-w-md rounded-2xl bg-white/80 backdrop-blur-sm p-6 sm:p-8 shadow-2xl border border-amber-100">
        <div className="text-center mb-6 sm:mb-8">
          {/* <div className="text-5xl mb-4">✨</div> */}
          <h2 className="text-2xl sm:text-3xl font-bold bg-linear-to-r from-amber-600 to-orange-500 bg-clip-text text-transparent">
            회원가입
          </h2>
          <p className="text-amber-700 mt-2 text-xs sm:text-sm">새로운 이야기를 시작하세요!</p>
        </div>

        {error && (
          <div className="mb-4 sm:mb-6 rounded-lg bg-red-50 border border-red-200 p-3 sm:p-4 text-red-700 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="text-base sm:text-lg">⚠️</span>
              <span className="text-sm sm:text-base">{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
          <div>
            <label className="mb-1.5 sm:mb-2 block text-xs sm:text-sm font-bold text-amber-900" htmlFor="email">
              이메일
            </label>
            <input
              className={`w-full appearance-none rounded-lg border-2 px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base leading-tight text-gray-700 bg-white/50 focus:outline-none focus:bg-white transition-all duration-200 shadow-sm ${
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
              <p className="mt-1.5 sm:mt-2 text-xs sm:text-sm text-red-600 flex items-center gap-1">
                <span>⚠️</span>
                <span>{emailError}</span>
              </p>
            )}
          </div>
          <div>
            <label className="mb-1.5 sm:mb-2 block text-xs sm:text-sm font-bold text-amber-900" htmlFor="password">
              비밀번호
            </label>
            <input
              className={`w-full appearance-none rounded-lg border-2 px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base leading-tight text-gray-700 bg-white/50 focus:outline-none focus:bg-white transition-all duration-200 shadow-sm ${
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
                // 비밀번호 변경 시 확인 필드도 다시 검증
                if (confirmPassword && confirmPasswordError) {
                  validateConfirmPassword(confirmPassword);
                }
              }}
              onBlur={handlePasswordBlur}
              required
            />
            {passwordError && (
              <p className="mt-1.5 sm:mt-2 text-xs sm:text-sm text-red-600 flex items-center gap-1">
                <span>⚠️</span>
                <span>{passwordError}</span>
              </p>
            )}
            <p className="mt-1.5 sm:mt-2 text-xs text-amber-600">
              * 8자 이상의 안전한 비밀번호를 사용하세요
            </p>
          </div>
          <div>
            <label className="mb-1.5 sm:mb-2 block text-xs sm:text-sm font-bold text-amber-900" htmlFor="confirmPassword">
              비밀번호 확인
            </label>
            <input
              className={`w-full appearance-none rounded-lg border-2 px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base leading-tight text-gray-700 bg-white/50 focus:outline-none focus:bg-white transition-all duration-200 shadow-sm ${
                confirmPasswordError
                  ? "border-red-400 focus:border-red-500"
                  : "border-amber-200 focus:border-amber-400"
              }`}
              id="confirmPassword"
              type="password"
              placeholder="비밀번호를 다시 입력하세요"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (confirmPasswordError) setConfirmPasswordError("");
              }}
              onBlur={handleConfirmPasswordBlur}
              required
            />
            {confirmPasswordError && (
              <p className="mt-1.5 sm:mt-2 text-xs sm:text-sm text-red-600 flex items-center gap-1">
                <span>⚠️</span>
                <span>{confirmPasswordError}</span>
              </p>
            )}
          </div>
          <div className="pt-3 sm:pt-4">
            <button
              className="w-full bg-linear-to-r from-amber-400 to-amber-500 text-gray-900 font-bold px-6 py-2.5 sm:py-3 text-sm sm:text-base rounded-full shadow-lg hover:shadow-xl hover:from-amber-500 hover:to-amber-600 focus:outline-none focus:ring-4 focus:ring-amber-300 transition-all duration-300 transform hover:scale-[1.02] active:scale-95"
              type="submit"
            >
              가입하기
            </button>
          </div>
          <div className="text-center pt-3 sm:pt-4">
            <p className="text-xs sm:text-sm text-amber-700">
              이미 계정이 있으신가요?{" "}
              <Link
                className="font-bold text-amber-600 hover:text-amber-800 underline decoration-2 decoration-amber-300 hover:decoration-amber-500 transition-colors"
                to="/login"
              >
                로그인
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterPage;
