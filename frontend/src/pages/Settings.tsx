import React, { useEffect, useState } from "react";
import { Mic, ArrowLeft, FileText } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { createVoiceClone, getVoices } from "../api/index";
import { AlertModal, ScriptModal } from "../components/Modal";
import type { VoiceResponse } from "./Creator";
import { usePostHog } from "@posthog/react";

// 허용되는 오디오 파일 확장자
const ALLOWED_AUDIO_TYPES = [".mp3", ".wav", ".m4a", ".flac", ".ogg"];
const MAX_FILE_SIZE = 30 * 1024 * 1024; // 30MB

interface ModalProps {
  title: string;
  message: string;
  submessage: string;
  buttonText: string;
  redirectTo: string;
}

export default function Settings() {
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [showModal, setShowModal] = useState<boolean>(false);
  const [modalProps, setModalProps] = useState<ModalProps>({
    title: "",
    message: "",
    submessage: "",
    buttonText: "",
    redirectTo: "",
  });
  const [showScriptModal, setShowScriptModal] = useState<boolean>(false);
  const navigate = useNavigate();
  const posthog = usePostHog();

  useEffect(() => {
    // 생성된 목소리가 하나라도 있다면 true
    const checkVoices = async () => {
      const voices: VoiceResponse[] = await getVoices();
      return voices.some((voice) => voice.is_custom);
    };

    const runCheck = async () => {
      const result = await checkVoices();

      if (result) {
        setShowModal(true);
        setModalProps({
          title: "음성 생성 제한 안내",
          message: "더 이상 목소리를 생성하실 수 없습니다.",
          submessage:
            "현재 정책에 따라 고객님께서는 최대 1개의 목소리만 보유하실 수 있습니다.",
          buttonText: "확인",
          redirectTo: "/",
        });
      }
    };

    runCheck(); // 정의된 runCheck 함수 실행
  }, []);
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
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

    // 오디오 길이 체크
    try {
      const duration = await getAudioDuration(selectedFile);
      if (duration < 150) { // 2분 30초 = 150초
        setShowModal(true);
        setModalProps({
          title: "오디오 길이 부족",
          message: "업로드한 오디오 파일이 너무 짧습니다.",
          submessage: `현재 오디오 길이: ${Math.floor(duration / 60)}분 ${Math.floor(duration % 60)}초. 최소 2분 30초 이상의 오디오가 필요합니다.`,
          buttonText: "확인",
          redirectTo: "",
        });
        setFile(null);
        // 파일 input 초기화
        const fileInput = document.getElementById("fileInput") as HTMLInputElement;
        if (fileInput) fileInput.value = "";
        return;
      }
    } catch (err) {
      console.error("오디오 길이 확인 중 오류:", err);
      setError("오디오 파일 정보를 읽는 중 오류가 발생했습니다.");
      setFile(null);
      return;
    }

    setFile(selectedFile);
    setError("");

    // 파일 업로드 성공 이벤트
    posthog?.capture("voice_file_uploaded", {
      file_type: fileExt,
      file_size_mb: (selectedFile.size / (1024 * 1024)).toFixed(2),
    });
  };

  // 오디오 파일의 길이를 가져오는 헬퍼 함수
  const getAudioDuration = (file: File): Promise<number> => {
    return new Promise((resolve, reject) => {
      const audio = new Audio();
      const objectUrl = URL.createObjectURL(file);

      audio.addEventListener("loadedmetadata", () => {
        URL.revokeObjectURL(objectUrl);
        resolve(audio.duration);
      });

      audio.addEventListener("error", () => {
        URL.revokeObjectURL(objectUrl);
        reject(new Error("오디오 파일을 로드할 수 없습니다."));
      });

      audio.src = objectUrl;
    });
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
      // API 호출
      await createVoiceClone({
        name,
        file,
        description: description.trim() || undefined, // 빈 문자열이면 undefined로
      });

      posthog?.capture("voice_creation_requested", { voice_name: name });
      // 성공 시 모달 표시
      setShowModal(true);
      setModalProps({
        title: "안내",
        message: "목소리 생성 요청이 성공적으로 접수되었습니다.",
        submessage:
          "생성완료까지 약 3분 소요됩니다. 백그라운드에서 처리 중이므로 다른 작업을 계속하셔도 됩니다.",
        buttonText: "확인",
        redirectTo: "/",
      });
      // 폼 초기화
      handleReset();
    } catch (err: unknown) {
      // Axios 에러 처리
      let errorMessage = "알 수 없는 오류가 발생했습니다.";

      if (err && typeof err === "object" && "response" in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        errorMessage = axiosError.response?.data?.detail || errorMessage;
      } else if (err && typeof err === "object" && "message" in err) {
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

  const closeModal = () => {
    setShowModal(false);
    // redirectTo가 빈 문자열이 아닌 경우에만 리다이렉트
    if (modalProps.redirectTo) {
      navigate(modalProps.redirectTo);
    }
  };

  return (
    <div className="min-h-screen py-6 sm:py-8 md:py-10 px-3 sm:px-4 md:px-5 font-sans">
      {/* 헤더 - 뒤로가기 버튼 */}
      <div className="relative flex items-center justify-center w-full mb-2 sm:mb-3">
        <button
          onClick={() => navigate("/")}
          className="absolute left-2 sm:left-4 md:left-8 bg-white rounded-full p-2.5 sm:p-3 md:p-3.5 shadow-xl hover:scale-110 hover:bg-yellow-400 hover:text-white transition-all"
        >
          <ArrowLeft className="w-6 h-6 sm:w-7 sm:h-7 md:w-8 md:h-8" />
        </button>
      </div>

      {/* 메인 카드 */}
      <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-lg p-6 sm:p-8 md:p-10">
        {/* 아이콘 */}
        <div className="flex justify-center items-center mb-3 sm:mb-4">
          <div className="w-16 h-16 sm:w-18 sm:h-18 md:w-20 md:h-20 rounded-full bg-yellow-100 flex justify-center items-center shadow-md">
            <Mic className="w-10 h-10 sm:w-11 sm:h-11 md:w-12 md:h-12 text-yellow-400" />
          </div>
        </div>

        {/* 제목 */}
        <h1 className="text-2xl sm:text-2xl md:text-3xl font-bold text-gray-900 mb-2 text-center">
          목소리 설정
        </h1>
        <p className="text-xs sm:text-sm text-gray-600 text-center mb-6 sm:mb-8 px-2">
          오디오 파일을 업로드하여 맞춤형 목소리를 생성합니다.
        </p>
        {/* 녹음용 대본 보기 버튼 */}
        <div className="flex justify-center mb-4 sm:mb-0">
          <button
            type="button"
            onClick={() => setShowScriptModal(true)}
            className="flex items-center gap-2 px-4 sm:px-5 md:px-6 py-2.5 sm:py-3 bg-yellow-50 border-2 border-yellow-400 text-yellow-700 rounded-lg font-semibold hover:bg-yellow-100 transition-all text-sm sm:text-base"
          >
            <FileText className="w-4 h-4 sm:w-5 sm:h-5" />
            녹음용 대본 보기
          </button>
        </div>

        {/* 설정 폼 */}
        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
          {/* 이름 입력 */}
          <div className="space-y-2">
            <label className="text-xs sm:text-sm font-semibold text-gray-700">
              목소리 이름 <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="예: 엄마 목소리, 아빠 목소리"
              className="w-full p-2.5 sm:p-3 text-sm sm:text-base border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all disabled:opacity-60"
              disabled={loading}
            />
          </div>

          {/* 오디오 파일 업로드 */}
          <div className="space-y-2">
            <label className="text-xs sm:text-sm font-semibold text-gray-700">
              오디오 파일 <span className="text-red-600">*</span>
            </label>
            <input
              id="fileInput"
              type="file"
              accept=".mp3,.wav,.m4a,.flac,.ogg"
              onChange={handleFileChange}
              className="w-full p-2 sm:p-2.5 text-xs sm:text-sm border border-gray-300 rounded-lg cursor-pointer focus:ring-2 focus:ring-yellow-400 focus:border-transparent disabled:opacity-60"
              disabled={loading}
            />

            {/* 선택된 파일 정보 */}
            {file && (
              <div className="p-2 sm:p-2.5 bg-gray-100 border border-gray-200 rounded-lg text-xs text-gray-700">
                📎 {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              </div>
            )}

            {/* 파일 안내 */}
            <div className="text-xs text-gray-600 leading-relaxed">
              • 허용 형식: mp3, wav, m4a, flac, ogg
              <br />
              • 최대 크기: 30MB
              <br />• 오디오 길이: 2분 30초 ~ 3분 (3분 초과 시 자동 트리밍)
              <p>
                • 오디오 길이 : 2분 30초 이상 ~ 3분 (3분 초과 시 자동으로 잘림)
              </p>
            </div>
          </div>

          {/* 버튼 그룹 */}
          <div className="flex gap-2 sm:gap-3 mt-5 sm:mt-6">
            <button
              type="submit"
              className={`flex-1 py-3 sm:py-3.5 text-sm sm:text-base font-semibold border-none rounded-lg transition-all ${
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
              className="flex-1 py-3 sm:py-3.5 text-sm sm:text-base font-semibold bg-gray-200 text-gray-700 border-none rounded-lg hover:bg-gray-300 transition-all disabled:opacity-60"
              disabled={loading}
            >
              초기화
            </button>
          </div>
        </form>

        {/* 성공 메시지 */}
        {message && (
          <div className="mt-4 sm:mt-5 p-3 sm:p-4 bg-green-100 border border-green-300 rounded-lg text-green-800 text-xs sm:text-sm leading-relaxed">
            {message}
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="mt-4 sm:mt-5 p-3 sm:p-4 bg-red-100 border border-red-300 rounded-lg text-red-800 text-xs sm:text-sm leading-relaxed">
            {error}
          </div>
        )}

        {/* 안내 사항 */}
        <div className="mt-6 sm:mt-8 p-4 sm:p-5 bg-yellow-50 border border-yellow-300 rounded-lg">
          <h3 className="text-sm sm:text-base font-semibold text-black mb-2 sm:mb-3">
            안내사항
          </h3>
          <ul className="m-0 pl-4 sm:pl-5 text-xs text-gray-800 leading-loose space-y-1">
            <li>🟡 목소리 생성 완료까지 약 3분 소요됩니다.</li>
            <li>🟡 2분 30초 미만의 오디오는 거부됩니다.</li>
            <li>🟡 3분 이상의 오디오는 자동으로 2분 59초로 트리밍됩니다.</li>
            <li>
              🟡 음성 학습 기능의 악용 사례를 방지하기 위해, 공인 또는 특정
              유명인의 목소리는 생성이 제한될 수 있습니다.
            </li>
          </ul>
        </div>
      </div>

      {/* Alert 모달 */}
      <AlertModal
        isOpen={showModal}
        onClose={closeModal}
        title={modalProps.title}
        message={modalProps.message}
        submessage={modalProps.submessage}
        buttonText={modalProps.buttonText}
        redirectTo={modalProps.redirectTo}
      />

      {/* Script 모달 */}
      <ScriptModal
        isOpen={showScriptModal}
        onClose={() => setShowScriptModal(false)}
      />
    </div>
  );
}
