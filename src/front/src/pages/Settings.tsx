import React, { useState } from "react";
import { Mic } from "lucide-react";

// 허용되는 오디오 파일 확장자
const ALLOWED_AUDIO_TYPES = [".mp3", ".wav", ".m4a", ".flac", ".ogg"];
const MAX_FILE_SIZE = 30 * 1024 * 1024; // 30MB

export default function Settings() {
  const [description, setDescription] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

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

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-5 font-sans">
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
        <form className="space-y-5"></form>
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
          <div className="flex gap-3 mt-6"></div>

          {/* 안내 사항 */}
      </div>
    </div>
  )
}
