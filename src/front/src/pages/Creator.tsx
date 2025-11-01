import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { createStorybook, getVoices } from "../api/index";
import StoryInput from "../components/StoryInput";
import BackButton from "../components/BackButton";

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
  const navigate = useNavigate();
  const [pages, setPages] = useState<Page[]>([
    { id: 1, image: null, story: "" },
  ]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("");

  // 음성 목록 가져오기
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const data: GetVoicesResponse = await getVoices();
        const voiceList = data.voices || [];
        setVoices(voiceList);
        if (voiceList.length > 0) {
          setSelectedVoice(voiceList[0].voice_id);
        }
        else{
          alert("목소리부터 넣고오세요")
          navigate("/settings")
        }
      } catch (error) {
        console.error("음성 목록 불러오기 실패:", error);
      }
    };

    fetchVoices();
  }, []);

  const addPage = () => {
    if (pages.length >= 10) {
      alert("동화는 최대 10페이지까지 만들 수 있어요.");
      return;
    }
    const newPage: Page = { id: Date.now(), image: null, story: "" };
    setPages([...pages, newPage]);
  };

  const removePage = (id: number) => {
    if (pages.length > 1) {
      setPages(pages.filter((page) => page.id !== id));
    } else {
      alert("최소 한 페이지는 있어야 해요.");
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
    setIsSubmitting(true);

    const stories = pages.map((page) => page.story);
    const images = pages.map((page) => page.image) as File[];

    if (images.some((img) => !img) || stories.some((s) => s.trim() === "")) {
      alert("모든 페이지에 이미지와 이야기를 채워주세요.");
      setIsSubmitting(false);
      return;
    }

    try {
      await createStorybook({
        stories,
        images,
        voice_id: selectedVoice,
      });

      alert("생성 완료까지 10분 걸림");
      navigate("/");
    } catch (error) {
      console.error("전송 실패:", error);
      alert("오류가 발생했어요. 다시 시도해주세요.");
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
    <div className=" min-h-screen p-8 font-sans relative">
      <div className="max-w-3xl mx-auto ">
        <BackButton/>
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
            disabled={pages.length >= 10}
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
    </div>
  );
}
