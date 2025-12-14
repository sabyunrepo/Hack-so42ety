import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { RECORDING_SECTIONS_PROCESSED } from "../types/script";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  message?: string;
  submessage?: string;
  buttonText?: string;
  redirectTo?: string; // 리다이렉트할 경로
  onConfirm?: () => void; // 확인 버튼 클릭 시 추가 동작
}

interface ScriptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ConfirmModal({
  isOpen,
  onClose,
  title,
  onConfirm,
}: ModalProps) {
  const handleConfirm = () => {
    // 추가 동작이 있으면 실행
    if (onConfirm) {
      onConfirm();
    }

    // 모달 닫기
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600/30 bg-opacity-50 flex items-center justify-center z-50 px-4">
      <div className="w-full max-w-sm sm:w-96 h-72 sm:h-80 relative bg-white rounded-[33px] shadow-xl">
        {/* X 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 sm:top-4 sm:right-4 w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center text-gray-600 hover:text-gray-800 text-xl sm:text-2xl font-bold"
        >
          ×
        </button>

        {/* 경고 아이콘 (노란색 원형) */}
        <div className="absolute top-12 sm:top-14 left-1/2 transform -translate-x-1/2">
          <div className="w-12 h-12 sm:w-14 sm:h-14 bg-amber-400 rounded-full flex items-center justify-center">
            <span className="text-white text-xl sm:text-2xl font-bold">!</span>
          </div>
        </div>

        {/* 제목 텍스트 */}
        <div className="absolute top-32 sm:top-36 left-1/2 transform -translate-x-1/2 text-center px-4">
          <h3 className="text-black text-xl sm:text-2xl font-bold font-['Roboto'] leading-7">
            {title || "삭제 하시겠습니까?"}
          </h3>
        </div>

        {/* 버튼들 */}
        <div className="absolute bottom-14 sm:bottom-16 left-1/2 transform -translate-x-1/2 flex gap-3 sm:gap-4">
          {/* 네 버튼 (취소) */}
          <button
            onClick={handleConfirm}
            className="w-24 h-11 sm:w-28 sm:h-12 bg-white rounded-xl border-[3px] border-amber-400 flex items-center justify-center hover:bg-gray-50 transition-colors"
          >
            <span className="text-black text-lg sm:text-xl font-normal font-['Roboto']">
              네
            </span>
          </button>

          {/* 아니오 버튼 (확인) */}
          <button
            onClick={onClose}
            className="w-24 h-11 sm:w-28 sm:h-12 bg-amber-400 rounded-xl border-[3px] border-amber-400 flex items-center justify-center hover:bg-amber-500 transition-colors"
          >
            <span className="text-black text-lg sm:text-xl font-normal font-['Roboto']">
              아니오
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

export function AlertModal({
  isOpen,
  onClose,
  title = "요청 완료!",
  message = "요청이 성공적으로 처리되었습니다.",
  submessage,
  buttonText = "확인",
  redirectTo,
  onConfirm,
}: ModalProps) {
  const navigate = useNavigate();

  const handleConfirm = () => {
    // 추가 동작이 있으면 실행
    if (onConfirm) {
      onConfirm();
    }

    // 모달 닫기
    onClose();

    // 리다이렉트가 설정되어 있으면 페이지 이동
    if (redirectTo) {
      navigate(redirectTo);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600/30 bg-opacity-50 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-xl p-6 sm:p-8 max-w-md mx-4 w-full shadow-2xl">
        {/* 제목 */}
        <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 text-center">
          {title}
        </h3>

        {/* 메시지 */}
        <div className="text-center mb-5 sm:mb-6">
          <p className="text-sm sm:text-base text-gray-600 mb-2">{message}</p>
          {submessage && (
            <p className="text-xs sm:text-sm text-gray-500 mt-2">
              {submessage}
            </p>
          )}
        </div>

        {/* 확인 버튼 */}
        <button
          onClick={handleConfirm}
          className="w-full py-2.5 sm:py-3 bg-yellow-400 text-white font-semibold rounded-lg hover:bg-yellow-500 transition-colors text-sm sm:text-base"
        >
          {buttonText}
        </button>
      </div>
    </div>
  );
}

// 녹음용 대본 섹션별 데이터

export function ScriptModal({ isOpen, onClose }: ScriptModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      // 전체 대본을 플레인 텍스트로 변환
      const fullScript = RECORDING_SECTIONS_PROCESSED.map((section) =>
        section.lines
          .map(
            (line) => `${line.korean}\n${line.english}\n${line.pronunciation}`
          )
          .join("\n\n")
      ).join("\n\n---\n\n");

      await navigator.clipboard.writeText(fullScript);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("복사 실패:", err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] sm:max-h-[85vh] flex flex-col shadow-2xl">
        <div className="overflow-y-auto">
          {/* 안내 메시지 */}
          <div className="px-4 sm:px-5 md:px-6 pt-3 sm:pt-4 pb-2">
            <div className="bg-blue-50 border-l-4 border-blue-400 rounded-r-lg p-3 sm:p-4">
              <ul className="text-xs sm:text-sm text-gray-700 leading-relaxed mt-2">
                <li>
                  <strong className="text-blue-600">감정/톤 참고:</strong> 각
                  문장의 감정 및 톤을 참고하여 또렷하고 자연스럽게 읽어주세요.
                  (대본은 참고용이며, 반드시 그대로 읽을 필요는 없습니다.)
                </li>

                <li>
                  <p className="mt-1">
                    <strong className="text-blue-600">
                      언어 선택 (권장) :
                    </strong>
                    <strong className="text-red-700">
                      {" "}
                      영어 대본으로 녹음 시 음성 생성 퀄리티가 가장 높습니다.
                      {" "}
                    </strong>
                    {/* <br /> */}
                    (한국어 녹음도 가능하지만, 최종 음성 품질을 위해 영어 녹음을
                    강력히 권장합니다.)
                  </p>
                </li>

                <li>
                  <strong className="text-blue-600">길이 제한 준수 :</strong>{" "}
                  녹음 길이가{" "}
                  <strong className="text-red-700">2분 30초 미만</strong>일 경우
                  TTS 생성이 불가합니다. (권장 녹음 시간은 2분 30초 초과 ~ 약
                  3분 입니다)
                </li>

                <li>
                  <strong className="text-blue-600">재녹음/이어읽기 :</strong>{" "}
                  대본을 모두 읽었는데도 2분 30초가 되지 않으면, 대본 처음부터
                  다시 읽어 이어서 녹음하셔도 괜찮습니다.
                </li>

                <li>
                  <strong className="text-blue-600">무음 구간 :</strong> 녹음 중
                  발생하는 무음 구간은 자동으로 삭제되므로, 여유 있게 진행하셔도
                  좋습니다.
                </li>
              </ul>
            </div>
          </div>

          {/* 대본 내용 - 스크롤 가능 */}
          <div className="flex-1  px-4 sm:px-5 md:px-6 py-3 sm:py-4">
            <div className="space-y-4 sm:space-y-5 md:space-y-6">
              {RECORDING_SECTIONS_PROCESSED.map((section, sectionIdx) => (
                <div
                  key={sectionIdx}
                  className="bg-gradient-to-br from-gray-50 to-white border border-gray-200 rounded-xl p-3 sm:p-4 md:p-5 shadow-sm hover:shadow-md transition-shadow"
                >
                  {/* 섹션 제목 */}
                  <div className="flex items-center gap-2 mb-3 sm:mb-4 pb-2 sm:pb-3 border-b border-gray-200">
                    {/* <span className="text-3xl">{section.emoji}</span> */}
                    <h4 className="text-base sm:text-lg font-bold text-gray-800">
                      {sectionIdx + 1}. {section.title}
                    </h4>
                  </div>

                  {/* 섹션 내용 */}
                  <div className="space-y-3 sm:space-y-4">
                    {section.lines.map((line, lineIdx) => (
                      <div
                        key={lineIdx}
                        className="bg-white rounded-lg p-3 sm:p-4 border border-gray-100"
                      >
                        {/* 감정/톤 태그 */}
                        <div className="mb-2">
                          <span className="inline-block px-2 sm:px-3 py-0.5 sm:py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full">
                            {line.emotion}
                          </span>
                        </div>
                        {/* 한글 원문 */}
                        <p className="text-sm sm:text-base font-medium text-gray-900 mb-2 leading-relaxed">
                          {line.korean}
                        </p>
                        {/* 영어 원문 */}
                        <p className="text-sm sm:text-base font-medium text-gray-900 mb-2 leading-relaxed">
                          {line.english}
                        </p>

                        {/* 한글 발음 */}
                        <p className="text-xs sm:text-sm text-gray-600 leading-relaxed">
                          🔊 {line.pronunciation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 하단 버튼 */}
        <div className="p-4 sm:p-5 md:p-6 border-t border-gray-200 bg-gray-50 flex gap-2 sm:gap-3 rounded-b-2xl">
          <button
            onClick={handleCopy}
            className={`flex-1 py-2.5 sm:py-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 shadow-sm text-sm sm:text-base ${
              copied
                ? "bg-green-500 text-white"
                : "bg-yellow-400 text-white hover:bg-yellow-500 hover:shadow-md"
            }`}
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 sm:w-5 sm:h-5" />
                복사 완료!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 sm:w-5 sm:h-5" />
                전체 대본 복사
              </>
            )}
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2.5 sm:py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100 transition-all shadow-sm text-sm sm:text-base"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
