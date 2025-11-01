import React, { useState } from "react";
import { Mic, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { createVoiceClone } from "../api/index";

// 허용되는 오디오 파일 확장자
const ALLOWED_AUDIO_TYPES = [".mp3", ".wav", ".m4a", ".flac", ".ogg"];
const MAX_FILE_SIZE = 30 * 1024 * 1024; // 30MB

export default function Settings() {
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // 파일 크기 체크
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError("파일 크기가 30MB를 초과합니다.");
      setFile(null);
      return;
    }

    // 파일 형식 체크
    const fileExt = "." + selectedFile.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_AUDIO_TYPES.includes(fileExt || "")) {
      setError(
        `지원하지 않는 파일 형식입니다. 허용: ${ALLOWED_AUDIO_TYPES.join(", ")}`
      );
      setFile(null);
      return;
    }

    setFile(selectedFile);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      setError("목소리 이름을 입력하세요.");
      return;
    }

    if (!file) {
      setError("오디오 파일을 선택하세요.");
      return;
    }

    setLoading(true);
    setMessage("");
    setError("");

    try {
      await createVoiceClone({
        name,
        file,
        description: description.trim() || undefined, // 빈 문자열이면 undefined로
      });

      setMessage(
        "✅ 목소리 생성 요청이 접수되었습니다! 백그라운드에서 처리 중입니다."
      );
      // 폼 초기화
      handleReset();
    } catch (err: unknown) {
      // Axios 에러 처리
      let errorMessage = "알 수 없는 오류가 발생했습니다.";
      
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        errorMessage = axiosError.response?.data?.detail || errorMessage;
      } else if (err && typeof err === 'object' && 'message' in err) {
        const error = err as { message: string };
        errorMessage = error.message;
      }
      
      setError(`❌ ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setName("");
    setDescription("");
    setFile(null);
    setMessage("");
    setError("");
    // 파일 input 초기화
    const fileInput = document.getElementById("fileInput") as HTMLInputElement;
    if (fileInput) fileInput.value = "";
  };

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-5 font-sans">
      {/* 헤더 - 뒤로가기 버튼 */}
      <div className="relative flex items-center justify-center w-full mb-3">
        <button
          onClick={() => navigate("/")}
          className="absolute left-8 bg-white rounded-full p-3.5 shadow-xl hover:scale-110 hover:bg-yellow-400 hover:text-white transition-all"
        >
          <ArrowLeft className="w-8 h-8" />
        </button>
      </div>

      {/* 메인 카드 */}
      <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-10">
        {/* 아이콘 */}
        <div className="flex justify-center items-center mb-4">
          <div className="w-20 h-20 rounded-full bg-yellow-100 flex justify-center items-center shadow-md">
            <Mic className="w-12 h-12 text-yellow-400" />
          </div>
        </div>

        {/* 제목 */}
        <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
          목소리 설정
        </h1>
        <p className="text-sm text-gray-600 text-center mb-8">
          오디오 파일을 업로드하여 맞춤형 목소리를 생성합니다.
        </p>

        {/* 설정 폼 */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 이름 입력 */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-700">
              목소리 이름 <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 엄마 목소리, 아빠 목소리"
              className="w-full p-3 text-sm border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all disabled:opacity-60"
              disabled={loading}
            />
          </div>

          {/* 오디오 파일 업로드 */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-700">
              오디오 파일 <span className="text-red-600">*</span>
            </label>
            <input
              id="fileInput"
              type="file"
              accept=".mp3,.wav,.m4a,.flac,.ogg"
              onChange={handleFileChange}
              className="w-full p-2 text-sm border border-gray-300 rounded-lg cursor-pointer focus:ring-2 focus:ring-yellow-400 focus:border-transparent disabled:opacity-60"
              disabled={loading}
            />

            {/* 선택된 파일 정보 */}
            {file && (
              <div className="p-2 bg-gray-100 border border-gray-200 rounded-lg text-xs text-gray-700">
                📎 {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
            )}
            
            {/* 파일 안내 */}
            <div className="text-xs text-gray-600 leading-relaxed">
              • 허용 형식: mp3, wav, m4a, flac, ogg<br />
              • 최대 크기: 30MB<br />
              • 오디오 길이: 2분 30초 ~ 3분 (3분 초과 시 자동 트리밍)
            </div>
          </div>

          {/* 버튼 그룹 */}
          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              className={`flex-1 py-3.5 text-sm font-semibold border-none rounded-lg transition-all ${
                loading
                  ? "bg-yellow-300 text-white opacity-60 cursor-not-allowed"
                  : "bg-yellow-400 text-white hover:bg-yellow-500"
              }`}
              disabled={loading}
            >
              {loading ? "업로드 중..." : "생성 요청"}
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="flex-1 py-3.5 text-sm font-semibold bg-gray-200 text-gray-700 border-none rounded-lg hover:bg-gray-300 transition-all disabled:opacity-60"
              disabled={loading}
            >
              초기화
            </button>
          </div>
        </form>

        {/* 성공 메시지 */}
        {message && (
          <div className="mt-5 p-4 bg-green-100 border border-green-300 rounded-lg text-green-800 text-sm leading-relaxed">
            {message}
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="mt-5 p-4 bg-red-100 border border-red-300 rounded-lg text-red-800 text-sm leading-relaxed">
            {error}
          </div>
        )}

        {/* 안내 사항 */}
        <div className="mt-8 p-5 bg-yellow-50 border border-yellow-300 rounded-lg">
          <h3 className="text-base font-semibold text-black mb-3">안내사항</h3>
          <ul className="m-0 pl-5 text-xs text-gray-800 leading-loose space-y-1">
            <li>🟡 목소리 생성 완료까지 약 3분 소요됩니다.</li>
            <li>🟡 2분 30초 미만의 오디오는 거부됩니다.</li>
            <li>🟡 3분 이상의 오디오는 자동으로 2분 59초로 트리밍됩니다.</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
