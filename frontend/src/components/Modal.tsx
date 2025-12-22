import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ENGLISH_SCRIPT_EXTENDED,
  KOREAN_SCRIPT_EXTENDED,
  type ScriptSection,
} from "../types/script";

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

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  shareUrl: string;
}

export function ConfirmModal({
  isOpen,
  onClose,
  title,
  message,
  submessage,
  onConfirm,
}: ModalProps) {
  const { t } = useTranslation('modal');

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
      <div className="flex flex-col justify-center items-center gap-3 w-full max-w-sm sm:w-96 h-72 sm:h-80 relative bg-white rounded-[33px] shadow-xl">
        {/* X 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 sm:top-4 sm:right-4 w-7 h-7 sm:w-8 sm:h-8 flex items-center justify-center text-gray-600 hover:text-gray-800 text-xl sm:text-2xl font-bold"
        >
          ×
        </button>

        {/* 경고 아이콘 (노란색 원형) */}
        <div className="mb-4 ">
          <div className="w-12 h-12 sm:w-14 sm:h-14 bg-amber-400 rounded-full flex items-center justify-center">
            <span className="text-white text-xl sm:text-2xl font-bold">!</span>
          </div>
        </div>

        {/* 제목 텍스트 */}
        <div className="  text-center px-4">
          <h3 className="text-black text-xl sm:text-2xl font-bold font-['Roboto'] leading-7">
            {title}
          </h3>
        </div>
        {/* 메시지 */}
        <div className="text-center mb-5 sm:mb-6">
          <p className="text-sm sm:text-base text-gray-600 mb-2">{message}</p>
          {submessage && (
            <p className="text-xs sm:text-sm text-gray-500 mt-2">
              {submessage}
            </p>
          )}
        </div>

        {/* 버튼들 */}
        <div className="  flex gap-3 sm:gap-4">
          {/* 네 버튼 (취소) */}
          <button
            onClick={handleConfirm}
            className="w-24 h-11 sm:w-28 sm:h-12 bg-white rounded-xl border-[3px] border-amber-400 flex items-center justify-center hover:bg-gray-50 transition-colors"
          >
            <span className="text-black text-lg sm:text-xl font-normal font-['Roboto']">
              {t('confirm.yes')}
            </span>
          </button>

          {/* 아니오 버튼 (확인) */}
          <button
            onClick={onClose}
            className="w-24 h-11 sm:w-28 sm:h-12 bg-amber-400 rounded-xl border-[3px] border-amber-400 flex items-center justify-center hover:bg-amber-500 transition-colors"
          >
            <span className="text-black text-lg sm:text-xl font-normal font-['Roboto']">
              {t('confirm.no')}
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
  title,
  message,
  submessage,
  buttonText,
  redirectTo,
  onConfirm,
}: ModalProps) {
  const { t } = useTranslation('modal');
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
          {title || t('alert.defaultTitle')}
        </h3>

        {/* 메시지 */}
        <div className="text-center mb-5 sm:mb-6">
          <p className="text-sm sm:text-base text-gray-600 mb-2">{message || t('alert.defaultMessage')}</p>
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
          {buttonText || t('alert.defaultButton')}
        </button>
      </div>
    </div>
  );
}

// 녹음용 대본 섹션별 데이터
type LanguageKey = "korean" | "english";

export function ScriptModal({ isOpen, onClose }: ScriptModalProps) {
  const { t } = useTranslation('modal');
  // 'english' 또는 'korean'으로 상태를 설정합니다.
  const [language, setLanguage] = useState<LanguageKey>("korean");

  const currentScriptData: ScriptSection[] =
    language === "korean" ? KOREAN_SCRIPT_EXTENDED : ENGLISH_SCRIPT_EXTENDED;

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    // select 요소의 value를 LanguageKey 타입으로 변환하여 상태를 업데이트합니다.
    setLanguage(e.target.value as LanguageKey);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] sm:max-h-[85vh] flex flex-col shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-4 sm:p-5 md:p-6 border-b border-gray-200 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-t-2xl">
          <div className=" flex flex-row gap-4 items-center">
            <h3 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-800">
              {" "}
              {t('script.title')}
            </h3>
            <div className="flex items-center gap-3 w-full sm:w-auto sm:flex-none">
              <select
                id="script-language-select"
                value={language}
                onChange={handleLanguageChange}
                className="py-2 px-3 border-2 border-gray-300 rounded-lg bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 transition-colors text-sm sm:text-base w-full sm:w-28"
              >
                <option value="korean">{t('script.languageSelect.korean')}</option>
                <option value="english">{t('script.languageSelect.english')}</option>
              </select>
            </div>
          </div>
          <div className=" flex flex-row gap-4 ">
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl sm:text-3xl font-bold leading-none transition-colors"
            >
              ×
            </button>
          </div>
        </div>
        <div className="overflow-y-auto">
          {/* 안내 메시지 */}
          <div className="px-4 sm:px-5 md:px-6 pt-3 sm:pt-4 pb-2">
            <div className="bg-blue-50 border-l-4 border-blue-400 rounded-r-lg p-3 sm:p-4">
              <ul className="text-xs sm:text-sm text-gray-700 leading-relaxed mt-2">
                <li>
                  <strong className="text-blue-600">{t('script.instructions.emotionLabel')}</strong> {t('script.instructions.emotion')}
                </li>

                <li>
                  <p className="mt-1">
                    <strong className="text-blue-600">{t('script.instructions.languageLabel')}</strong>{" "}
                    {t('script.instructions.language')}
                  </p>
                </li>

                <li>
                  <strong className="text-blue-600">{t('script.instructions.lengthLabel')}</strong>{" "}
                  {t('script.instructions.length')}{" "}
                  {t('script.instructions.lengthRecommendation')}
                </li>

                <li>
                  <strong className="text-blue-600">{t('script.instructions.retryLabel')}</strong>{" "}
                  {t('script.instructions.retry')}
                </li>

                <li>
                  <strong className="text-blue-600">{t('script.instructions.silenceLabel')}</strong>{" "}
                  {t('script.instructions.silence')}
                </li>
              </ul>
            </div>
          </div>

          {/* 대본 내용 - 스크롤 가능 */}
          <div className="flex-1  px-4 sm:px-5 md:px-6 py-3 sm:py-4">
            <div className="space-y-4 sm:space-y-5 md:space-y-6">
              {currentScriptData.map((section, sectionIdx) => (
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
                        {/*  원문 */}
                        <p className="text-sm sm:text-base font-medium text-gray-900 mb-2 leading-relaxed">
                          {line.text}
                        </p>

                        {/* 발음 */}
                        {language === "english" && (
                          <p className="text-xs sm:text-sm text-gray-600 leading-relaxed">
                            {line.pronunciation}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ShareModal({ isOpen, onClose, shareUrl }: ShareModalProps) {
  const { t } = useTranslation('modal');
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-5 sm:p-6 border-b border-gray-200 bg-gradient-to-r from-amber-50 to-orange-50 rounded-t-2xl">
          <h3 className="text-xl sm:text-2xl font-bold text-gray-800">
            {t('share.title')}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-3xl font-bold leading-none transition-colors"
          >
            ×
          </button>
        </div>

        {/* 내용 */}
        <div className="p-5 sm:p-6">
          <p className="text-sm sm:text-base text-gray-600 mb-4">
            {t('share.message')}
          </p>

          {/* 링크 표시 */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 sm:p-4 mb-4 break-all">
            <code className="text-xs sm:text-sm text-gray-800">
              {shareUrl}
            </code>
          </div>

          {/* 복사 버튼 */}
          <button
            onClick={handleCopy}
            className={`w-full py-3 sm:py-3.5 font-semibold rounded-lg transition-all ${
              copied
                ? 'bg-green-500 text-white'
                : 'bg-amber-400 text-gray-900 hover:bg-amber-500'
            }`}
          >
            {copied ? t('share.copied') : t('share.copyButton')}
          </button>
        </div>
      </div>
    </div>
  );
}
