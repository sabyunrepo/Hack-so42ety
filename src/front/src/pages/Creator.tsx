import { useState, useEffect } from "react";
import { createStorybook, getVoices } from "../api/index";
import StoryInput from "../components/StoryInput";
import BackButton from "../components/BackButton";
import { AlertModal } from "../components/Modal";

interface Page {
  id: number;
  image: File | null;
  story: string;
}

interface Voice {
  voice_id: string;
  voice_label: string;
  state: string;
  preview_url?: string;
}

interface GetVoicesResponse {
  voices: Voice[];
}

export default function Creator() {
  const [pages, setPages] = useState<Page[]>([
    { id: 1, image: null, story: "" },
  ]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [showVoiceWarningModal, setShowVoiceWarningModal] = useState(false);
  const [showMaxPageModal, setShowMaxPageModal] = useState(false);
  const [showMinPageModal, setShowMinPageModal] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);

  // 음성 목록 가져오기
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const data: GetVoicesResponse = await getVoices();
        const voiceList = data.voices || [];
        setVoices(voiceList);
        if (voiceList.length > 0) {
          setSelectedVoice(voiceList[0].voice_id);
        } else {
          setShowVoiceWarningModal(true);
        }
      } catch (error) {
        console.error("음성 목록 불러오기 실패:", error);
      }
    };

    fetchVoices();
  }, []);

  const addPage = () => {
    if (pages.length > 9) {
      setShowMaxPageModal(true);
      return;
    }
    const newPage: Page = { id: Date.now(), image: null, story: "" };
    setPages([...pages, newPage]);
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

    const stories = pages.map((page) => page.story);
    const images = pages.map((page) => page.image) as File[];

    if (images.some((img) => !img) || stories.some((s) => s.trim() === "")) {
      setShowValidationModal(true);
      setIsSubmitting(false);
      return;
    }

    try {
      await createStorybook({
        stories,
        images,
        voice_id: selectedVoice,
      });

      setShowSuccessModal(true);
    } catch (error) {
      console.error("전송 실패:", error);
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
    <div className="p-8 font-sans relative">
      <div className="max-w-3xl mx-auto ">
        <BackButton />
        {/* 상단 컨트롤 */}
        <div className="flex items-center justify-between gap-4 pt-24">
          {/* 음성 선택 */}
          {voices.length > 0 && (
            <div className="flex items-center gap-2">
              <label
                htmlFor="voice-select"
                className="text-gray-700 font-medium"
              >
                음성:
              </label>
              <select
                id="voice-select"
                value={selectedVoice}
                onChange={(e) => {
                  setSelectedVoice(e.target.value);
                }}
                className="bg-white border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-300"
              >
                {voices.map((voice) => (
                  <option
                    key={voice.voice_id}
                    value={voice.voice_id}
                    disabled={voice.state !== "success"}
                  >
                    {voice.voice_label}
                    {voice.state !== "success" && " - 생성중"}
                  </option>
                ))}
              </select>

              {/* 미리듣기 버튼 */}
              {voices.find((v) => v.voice_id === selectedVoice) && (
                <button
                  onClick={() =>
                    playPreview(
                      voices.find((v) => v.voice_id === selectedVoice)
                        ?.preview_url
                    )
                  }
                  className="bg-white border border-gray-300 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors"
                  title="음성 미리듣기"
                >
                  🔊
                </button>
              )}
            </div>
          )}

          {/* 생성 완료 버튼 */}
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="bg-amber-300 text-gray-800 font-semibold px-5 py-2 rounded-full shadow-sm hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "만드는 중..." : "생성 완료"}
          </button>
        </div>

        {/* 페이지 리스트 */}
        <div className="mt-16 space-y-8">
          {pages.map((page, index) => (
            <div
              key={page.id}
              className="flex gap-4 items-start justify-center h-44"
            >
              {/* 페이지 번호 배지 */}
              <div className="pt-2 h-full flex items-center">
                <div className="flex items-center justify-center bg-[#F2BF27] w-8 h-8 rounded-full shadow-md font-bold text-white text-lg">
                  {index + 1}
                </div>
              </div>

              {/* 스토리 입력 컴포넌트 */}
              <div className="flex-1">
                <StoryInput page={page} updatePage={updatePage} />
              </div>
              {pages.length > 1 && (
                <button
                  onClick={() => removePage(page.id)}
                  className=" text-gray-400 hover:text-red-500 transition-colors"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-6 w-6"
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
              )}
            </div>
          ))}
        </div>

        {/* 페이지 추가 버튼 */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={addPage}
            className="w-[680px] border-2 border-dashed border-gray-400 rounded-2xl py-6 flex justify-center items-center cursor-pointer hover:bg-amber-100/50 transition-colors disabled:opacity-50"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-10 w-10 text-gray-500"
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
        title="목소리 설정 필요"
        message="목소리부터 넣고오세요"
        buttonText="목소리 설정하러 가기"
        redirectTo="/settings"
      />

      {/* 최대 페이지 제한 모달 */}
      <AlertModal
        isOpen={showMaxPageModal}
        onClose={() => setShowMaxPageModal(false)}
        title="페이지 제한"
        message="동화는 최대 10페이지까지 만들 수 있어요."
        buttonText="확인"
      />

      {/* 최소 페이지 제한 모달 */}
      <AlertModal
        isOpen={showMinPageModal}
        onClose={() => setShowMinPageModal(false)}
        title="페이지 제한"
        message="최소 한 페이지는 있어야 해요."
        buttonText="확인"
      />

      {/* 검증 실패 모달 */}
      <AlertModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        title="입력 확인"
        message="모든 페이지에 이미지와 이야기를 채워주세요."
        buttonText="확인"
      />

      {/* 성공 모달 */}
      <AlertModal
        isOpen={showSuccessModal}
        onClose={() => setShowSuccessModal(false)}
        title="동화책 생성"
        message="생성 완료까지 10분 걸림"
        buttonText="확인"
        redirectTo="/"
      />

      {/* 에러 모달 */}
      <AlertModal
        isOpen={showErrorModal}
        onClose={() => setShowErrorModal(false)}
        title="오류 발생"
        message="오류가 발생했어요. 다시 시도해주세요."
        buttonText="확인"
      />
    </div>
  );
}
