// src/pages/Viewer.tsx
import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import HTMLFlipBook from "react-pageflip";
import { X } from "lucide-react";
import MoriAI_Icon from "../assets/MoriAI_Icon.svg";
import { getStorybookById } from "../api/index";
import ClickableText from "../components/ClickableText";
import AudioPlayer from "../components/AudioPlayer";

// --- 타입 정의 ---

// 2. 책 내부의 'dialogue' 데이터 타입
interface Dialogue {
  id: string | number;
  text: string;
  part_audio_url: string;
}

// 3. 책의 'page' 데이터 타입
interface PageData {
  id: string | number;
  type: "video" | "image" | string; // 'video' 외 다른 타입이 있다면 추가
  content: string; // 이미지 또는 비디오 URL
  dialogues: Dialogue[];
}

// 4. API로부터 받는 'book' 데이터의 전체 구조
interface BookData {
  title: string;
  cover_image: string;
  pages: PageData[];
}

// 5. react-pageflip 라이브러리의 ref가 노출하는 API 타입
// (실제 라이브러리에 타입이 있다면 @types/react-pageflip 임포트로 대체 가능)
interface PageFlipApi {
  flipNext: () => void;
  flipPrev: () => void;
}

interface HTMLFlipBookRef {
  pageFlip: () => PageFlipApi;
}

type PageProps = {
  children: React.ReactNode;
  className?: string;
  "data-density"?: "hard" | "soft";
};

const Page = React.forwardRef<HTMLDivElement, PageProps>(
  ({ children, className, "data-density": dataDensity }, ref) => {
    return (
      <div
        ref={ref}
        className={className || "demoPage"}
        data-density={dataDensity}
      >
        {children}
      </div>
    );
  }
);
// --- 컴포넌트 ---

const Viewer: React.FC = () => {
  // 6. useParams에 제네릭을 사용하여 bookId의 타입을 string으로 지정
  const { bookId } = useParams<{ bookId: string }>();

  // 7. useState에 타입 적용
  const [book, setBook] = useState<BookData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isError, setIsError] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<number>(0);

  // 8. useRef에 타입 적용
  const bookRef = useRef<HTMLFlipBookRef | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!bookId) {
      setIsLoading(false);
      return;
    }

    const fetchBook = async () => {
      try {
        setIsLoading(true);
        setIsError(false);
        // getStorybookById가 BookData 타입을 반환한다고 가정
        const data: BookData = await getStorybookById(bookId);
        setBook(data);
      } catch (error) {
        setIsError(true);
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchBook();
  }, [bookId]);

  // 9. ref 사용 시 null 체크 추가 (TypeScript가 강제)
  const handleNextPage = () => {
    if (bookRef.current) {
      bookRef.current.pageFlip().flipNext();
      setCurrentPage((prev) => Math.min(prev + 1, totalPages - 1));
    }
  };

  const handlePrevPage = () => {
    if (bookRef.current) {
      bookRef.current.pageFlip().flipPrev();
      setCurrentPage((prev) => Math.max(prev - 1, 0));
    }
  };

  // Calculate total pages (cover + content pages + back cover)
  const totalPages = book ? book.pages.length * 2 + 2 : 0;

  if (isLoading) {
    return (
      <div className="p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="animate-spin rounded-full h-20 w-20 border-4 border-amber-200 border-t-amber-500"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-20 w-20 border-2 border-amber-400/40"></div>
          </div>
          <div className="text-2xl font-bold text-amber-900 tracking-wide">책을 불러오는 중...</div>
          <div className="flex gap-2">
            <div className="w-3 h-3 bg-amber-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-3 h-3 bg-amber-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-3 h-3 bg-amber-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-8 max-w-md text-center border-2 border-red-200">
          <div className="text-6xl mb-4 animate-pulse">⚠️</div>
          <div className="text-2xl font-bold text-red-600 mb-2">오류가 발생했습니다</div>
          <p className="text-gray-600 mb-6">책을 불러올 수 없습니다. 다시 시도해주세요.</p>
          <button
            onClick={() => navigate("/")}
            className="px-6 py-3 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300"
          >
            책장으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  // 10. book 객체가 null이 아님을 TypeScript에 확인
  if (!book) {
    return (
      <div className="p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-8 max-w-md text-center">
          <div className="text-6xl mb-4">📚</div>
          <div className="text-2xl font-bold text-amber-900 mb-2">책을 찾을 수 없습니다</div>
          <button
            onClick={() => navigate("/")}
            className="mt-4 px-6 py-3 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300"
          >
            책장으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className=" p-7 flex flex-col justify-center items-center bg-gradient-to-br from-orange-50 via-amber-50/50 to-orange-50 min-h-full">
      {/* Header with title and close button */}
      <div className="relative flex items-center justify-center w-full mb-6">
        <h1 className="text-4xl font-bold text-amber-900 tracking-tight drop-shadow-sm">{book.title || "제목 없음"}</h1>
        <button
          onClick={() => navigate("/")}
          className="absolute right-8 bg-white rounded-full p-3.5 shadow-xl hover:scale-110 hover:bg-gradient-to-br hover:from-amber-400 hover:to-amber-500 hover:text-white transition-all duration-300 border-2 border-amber-200/50"
        >
          <X className="w-8 h-8" />
        </button>
      </div>
      <HTMLFlipBook
        width={400}
        height={550}
        showCover={true}
        useMouseEvents={true}
        ref={bookRef}
        maxShadowOpacity={0.5}
        startPage={0}
        drawShadow={true}
        showPageCorners={true}
        flippingTime={800}
        disableFlipByClick={true}
        clickEventForward={false}
        size="fixed"
        onFlip={(e: number | { data: number }) => {
          const pageNum = typeof e === 'object' ? e.data : e;
          setCurrentPage(pageNum);
        }}
      >
        {/* 첫 번째 페이지: 커버 이미지 */}
        {/* A_FIX: <div>를 <Page>로 변경 */}
        <Page
          className="demoPage border bg-white shadow-2xl/30"
          data-density="hard"
        >
          <img
            src={`${book.cover_image}`}
            alt="커버"
            className="w-full h-full object-cover"
          />
        </Page>

        {/* 책 내용 */}
        {book.pages.map((pageData: PageData) => [
          // 이미지 (오른쪽 접힌 부분 효과)
          // A_FIX: <div>를 <Page>로 변경
          <Page
            key={`image-${pageData.id}`}
            className="relative bg-white flex flex-col justify-center items-center p-5 shadow-2xl/30 "
          >
            {pageData.type === "video" ? (
              <video muted autoPlay loop className="h-full w-full object-cover">
                <source src={`${pageData.content}`} type="video/mp4" />
              </video>
            ) : (
              <img
                src={`${pageData.content}`}
                className="h-full w-full object-cover"
              />
            )}
            {/* ... (그라데이션 효과) ... */}
            <div
              className="pointer-events-none absolute inset-y-0 right-0 w-[10%]"
              style={{
                background:
                  "linear-gradient(to left, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.4) 20%, rgba(0,0,0,0.1) 60%, transparent 100%)",
              }}
            ></div>
            <div
              className="pointer-events-none absolute inset-y-0 left-0 w-[15%]"
              style={{
                background:
                  "linear-gradient(to right, rgba(0,0,0,0.1) 20%, transparent 100%)",
              }}
            ></div>
          </Page>,

          // 글자 (왼쪽 접힌 부분 효과)
          // A_FIX: <div>를 <Page>로 변경
          <Page
            key={`text-${pageData.id}`}
            className="relative w-full h-full bg-white flex flex-col justify-center items-center p-10 shadow-2xl/30 "
          >
            {/* ... (그라데이션 효과) ... */}
            <div
              className="pointer-events-none absolute inset-y-0 left-0 w-[15%]"
              style={{
                background:
                  "linear-gradient(to right, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.4) 20%, rgba(0,0,0,0.1) 60%, transparent 100%)",
              }}
            ></div>
            <div
              className="pointer-events-none absolute inset-y-0 right-0 w-[10%]"
              style={{
                background:
                  "linear-gradient(to left, rgba(0,0,0,0.1) 20%, transparent 100%)",
              }}
            ></div>

            {pageData.dialogues.map((dialogue: Dialogue) => (
              <div
                key={dialogue.id}
                className="relative"
                onClick={(e: React.MouseEvent) => e.stopPropagation()}
                onMouseDown={(e: React.MouseEvent) => e.stopPropagation()}
                onTouchStart={(e: React.TouchEvent) => e.stopPropagation()}
              >
                <ClickableText text={dialogue.text} book_id={bookId!} />
                <AudioPlayer src={`${dialogue.part_audio_url}`} />
              </div>
            ))}
          </Page>,
        ])}

        {/* 마지막 페이지: 뒷면 커버 */}
        {/* A_FIX: <div>를 <Page>로 변경 */}
        <Page
          className="demoPage border bg-[#f2bf27] relative w-full min-h-[200px] shadow-2xl/30"
          data-density="hard"
        >
          <img
            src={MoriAI_Icon}
            alt="MoriAI Logo"
            className="h-17 absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          />
        </Page>
      </HTMLFlipBook>

      {/* Navigation controls */}
      <div className="w-full flex justify-center items-center gap-8 mt-6">
        {/* Previous button */}
        <button
          onClick={handlePrevPage}
          disabled={currentPage === 0}
          className="bg-gradient-to-br from-white to-amber-50 rounded-full p-4 shadow-xl hover:scale-110 hover:shadow-2xl hover:from-amber-400 hover:to-amber-500 hover:text-white transition-all duration-300 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:from-white disabled:hover:to-amber-50 disabled:hover:text-gray-800 border-2 border-amber-200/50"
        >
          <svg
            className="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>

        {/* Page number indicator */}
        <div className="flex flex-col items-center">
          {/* <div className="bg-white/90 backdrop-blur-sm px-6 py-3 rounded-full shadow-lg border-2 border-amber-200">
            <span className="text-lg font-bold text-amber-900">
              {currentPage + 1} / {totalPages}
            </span>
          </div> */}
          {/* <p className="text-sm text-amber-700 mt-2 font-medium">페이지</p> */}
        </div>

        {/* Next button */}
        <button
          onClick={handleNextPage}
          disabled={currentPage === totalPages - 1}
          className="bg-gradient-to-br from-white to-amber-50 rounded-full p-4 shadow-xl hover:scale-110 hover:shadow-2xl hover:from-amber-400 hover:to-amber-500 hover:text-white transition-all duration-300 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:from-white disabled:hover:to-amber-50 disabled:hover:text-gray-800 border-2 border-amber-200/50"
        >
          <svg
            className="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default Viewer;
