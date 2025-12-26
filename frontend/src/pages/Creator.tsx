import { useState, useEffect } from "react";
import { createStorybook, getVoices, getAllStorybooks } from "../api/index";
import StoryInput from "../components/StoryInput";
import BackButton from "../components/BackButton";
import { AlertModal } from "../components/Modal";
import { getUserFriendlyErrorMessage } from "../utils/errorHandler";
import { usePostHog } from "@posthog/react";
import { useTranslation } from "react-i18next";

interface Page {
  id: number;
  image: File | null;
  story: string;
}

// 백엔드 응답 형식

export interface VoiceResponse {
  voice_id: string;
  name: string;
  language: string;
  gender: string;
  preview_url: string;
  category: string;
  visibility: string;
  status: string;
  is_custom: boolean;
}

export default function Creator() {
  const { t } = useTranslation("creator");
  const [pages, setPages] = useState<Page[]>([
    { id: 1, image: null, story: "" },
  ]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [voices, setVoices] = useState<VoiceResponse[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [selectedLevel, setSelectedLevel] = useState<string>("1");
  const [showVoiceWarningModal, setShowVoiceWarningModal] = useState(false);
  const [showMaxPageModal, setShowMaxPageModal] = useState(false);
  const [showMinPageModal, setShowMinPageModal] = useState(false);
  const [showMaxBooksModal, setShowMaxBooksModal] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const posthog = usePostHog();

  // 음성 목록 가져오기
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        // 백엔드는 배열을 직접 반환
        const voiceList: VoiceResponse[] = await getVoices();
        setVoices(voiceList);
        if (voiceList.length > 0) {
          setSelectedVoice(voiceList[0].voice_id);
        } else {
          setShowVoiceWarningModal(true);
        }
      } catch (error) {
        setErrorMessage(getUserFriendlyErrorMessage(error));
        setShowErrorModal(true);
      }
    };

    fetchVoices();
  }, []);

  const addPage = () => {
    if (pages.length >= 5) {
      setShowMaxPageModal(true);
      return;
    }
    const newPage: Page = { id: Date.now(), image: null, story: "" };
    setPages([...pages, newPage]);
    console.log("voices 길이 : ", voices.length);
  };

  const removePage = (id: number) => {
    console.log("현재 페이지 수:", pages.length);

    if (pages.length > 1) {
      setPages(pages.filter((page) => page.id !== id));
    } else {
      setShowMinPageModal(true);
    }
  };

  const updatePage = <K extends keyof Page>(
    id: number,
    field: K,
    value: Page[K]
  ) => {
    setPages(
      pages.map((page) => (page.id === id ? { ...page, [field]: value } : page))
    );
  };

  const handleSubmit = async () => {
    console.log("현재 페이지 수:", pages.length);

    setIsSubmitting(true);

    try {
      // 책 권수 확인
      const books = await getAllStorybooks();
      if (books.length >= 5) {
        setShowMaxBooksModal(true);
        setIsSubmitting(false);
        return;
      }

      const stories = pages.map((page) => page.story);
      const images = pages.map((page) => page.image) as File[];

      if (images.some((img) => !img) || stories.some((s) => s.trim() === "")) {
        setShowValidationModal(true);
        setIsSubmitting(false);
        return;
      }

      await createStorybook({
        stories,
        images,
        voice_id: selectedVoice,
        level: selectedLevel,
      });

      posthog?.capture("book_creation_requested", { page_count: pages.length });
      setShowSuccessModal(true);
    } catch (error) {
      setErrorMessage(getUserFriendlyErrorMessage(error));
      setShowErrorModal(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const playPreview = (previewUrl?: string) => {
    if (previewUrl) {
      const audio = new Audio(previewUrl);
      audio.play();
    }
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 font-sans relative">
      <div className="max-w-3xl mx-auto">
        <BackButton />
        {/* 상단 컨트롤 */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4 pt-16 sm:pt-20 md:pt-24">
          {/* 음성 선택 */}
          {voices.length > 0 && (
            <div className="flex items-center gap-2 flex-1 sm:flex-initial">
              <label
                htmlFor="voice-select"
                className="text-gray-700 font-medium text-sm sm:text-base whitespace-nowrap"
              >
                {t("voice")}
              </label>
              <select
                id="voice-select"
                value={selectedVoice}
                onChange={(e) => {
                  setSelectedVoice(e.target.value);
                }}
                className="bg-white border border-gray-300 rounded-lg px-2 sm:px-3 py-1.5 sm:py-2 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-amber-300 flex-1 sm:flex-initial"
              >
                {voices.map((voice) => (
                  <option
                    key={voice.voice_id}
                    value={voice.voice_id}
                    // disabled={voice.state !== "success"}
                  >
                    {voice.name}
                    {/* {voice.status !== "completed" && " - 프리뷰 생성중"} */}
                  </option>
                ))}
              </select>

              {/* 미리듣기 버튼 */}
              {voices.find((v) => v.voice_id === selectedVoice) && (
                <div className="relative group">
                  <button
                    onClick={() =>
                      playPreview(
                        voices.find((v) => v.voice_id === selectedVoice)
                          ?.preview_url
                      )
                    }
                    disabled={
                      !voices.find((v) => v.voice_id === selectedVoice)
                        ?.preview_url
                    }
                    className={`border rounded-lg px-2 sm:px-3 py-1.5 sm:py-2 text-sm sm:text-base transition-colors ${
                      voices.find((v) => v.voice_id === selectedVoice)
                        ?.preview_url
                        ? "bg-white border-gray-300 hover:bg-gray-50 cursor-pointer"
                        : "bg-gray-100 border-gray-200 cursor-not-allowed opacity-60"
                    }`}
                  >
                    🔊
                  </button>
                  {/* 툴팁 */}
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 sm:px-3 py-1.5 sm:py-2 bg-gray-800 text-white text-xs sm:text-sm rounded-lg shadow-lg opacity-0 group-hover:opacity-50 transition-opacity pointer-events-none whitespace-nowrap z-10">
                    {voices.find((v) => v.voice_id === selectedVoice)
                      ?.preview_url
                      ? t("voicePreview")
                      : t("voicePreviewNotAvailable")}
                    {/* 툴팁 화살표 */}
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-800"></div>
                  </div>
                </div>
              )}
            </div>
          )}
          {/* 레벨 설정 */}
          <div className="flex items-center gap-2 flex-1 sm:flex-initial">
            <label
              htmlFor="voice-select"
              className="text-gray-700 font-medium text-sm sm:text-base whitespace-nowrap"
            >
              {t("level")}
            </label>
            <select
              id="voice-select"
              value={selectedLevel}
              onChange={(e) => {
                setSelectedLevel(e.target.value);
              }}
              className="bg-white border border-gray-300 rounded-lg px-2 sm:px-3 py-1.5 sm:py-2 text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-amber-300 flex-1 sm:flex-initial"
            >
              <option value={1}>{t("levelOption1")}</option>
              <option value={2}>{t("levelOption2")}</option>
              <option value={3}>{t("levelOption3")}</option>
            </select>
          </div>

          {/* 생성 완료 버튼 */}
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="bg-amber-300 text-gray-800 font-semibold px-4 sm:px-5 py-2 sm:py-2.5 text-sm sm:text-base rounded-full shadow-sm hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
          >
            {isSubmitting ? t("creating") : t("creationComplete")}
          </button>
        </div>

        {/* 페이지 리스트 */}
        <div className="mt-8 sm:mt-12 md:mt-16 space-y-6 sm:space-y-8">
          {pages.map((page, index) => (
            <div
              key={page.id}
              className="flex gap-3 sm:gap-4 items-start justify-center min-h-[10rem] sm:min-h-[11rem] md:min-h-[11rem]"
            >
              {/* 페이지 번호 배지 */}
              <div className="pt-2 h-full flex items-center flex-shrink-0">
                <div className="flex items-center justify-center bg-[#F2BF27] w-7 h-7 sm:w-8 sm:h-8 rounded-full shadow-md font-bold text-white text-base sm:text-lg">
                  {index + 1}
                </div>
              </div>

              {/* 스토리 입력 컴포넌트 */}
              <div className="flex-1">
                <StoryInput page={page} updatePage={updatePage} />
              </div>
                <button
                  onClick={() => removePage(page.id)}
                  className="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5 sm:h-6 sm:w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
            </div>
          ))}
        </div>

        {/* 페이지 추가 버튼 */}
        <div className="mt-4 sm:mt-6 flex justify-center">
          <button
            onClick={addPage}
            className="w-full max-w-[680px] border-2 border-dashed border-gray-400 rounded-2xl py-5 sm:py-6 flex justify-center items-center cursor-pointer hover:bg-amber-100/50 transition-colors disabled:opacity-50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-8 w-8 sm:h-10 sm:w-10 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4v16m8-8H4"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* 목소리 경고 모달 */}
      <AlertModal
        isOpen={showVoiceWarningModal}
        onClose={() => setShowVoiceWarningModal(false)}
        title={t("noVoice")}
        message={t("noVoiceWarning")}
        buttonText={t("goToSettings")}
        redirectTo="/settings"
      />

      {/* 최대 페이지 제한 모달 */}
      <AlertModal
        isOpen={showMaxPageModal}
        onClose={() => setShowMaxPageModal(false)}
        title={t("modals.pageLimit.title")}
        message={t("modals.pageLimit.maxPages")}
        buttonText={t("common:button.confirm")}
      />

      {/* 최소 페이지 제한 모달 */}
      <AlertModal
        isOpen={showMinPageModal}
        onClose={() => setShowMinPageModal(false)}
        title={t("modals.pageLimit.title")}
        message={t("modals.pageLimit.minPages")}
        buttonText={t("common:button.confirm")}
      />

      {/* 최대 책 권수 제한 모달 */}
      <AlertModal
        isOpen={showMaxBooksModal}
        onClose={() => setShowMaxBooksModal(false)}
        title={t("modals.bookLimit.title")}
        message={t("modals.bookLimit.message")}
        buttonText={t("common:button.confirm")}
      />

      {/* 검증 실패 모달 */}
      <AlertModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        title={t("modals.validation.title")}
        message={t("modals.validation.message")}
        buttonText={t("common:button.confirm")}
      />

      {/* 성공 모달 */}
      <AlertModal
        isOpen={showSuccessModal}
        onClose={() => setShowSuccessModal(false)}
        title={t("modals.success.title")}
        message={t("modals.success.message")}
        buttonText={t("common:button.confirm")}
        redirectTo="/"
      />

      {/* 에러 모달 */}
      <AlertModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title={t("modals.error.title")}
        message={errorMessage || t("modals.error.message")}
        buttonText={t("common:button.confirm")}
      />
    </div>
  );
}
