// src/pages/Viewer.tsx
import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import HTMLFlipBook from "react-pageflip";
import { X, Share2 } from "lucide-react";
import MoriAI_Icon from "../assets/MoriAI_Icon.svg";
import { getStorybookById, toggleBookShare } from "../api/index";
import ClickableText from "../components/ClickableText";
import AudioPlayer from "../components/AudioPlayer";
import type { BookData, PageData, Dialogue } from "../types/book";
import { getDialogueText, getDialogueAudioUrl } from "../types/book";
import { getUserFriendlyErrorMessage } from "../utils/errorHandler";
import { usePostHog } from "@posthog/react";
import { useTranslation } from "react-i18next";
import { ShareModal } from "../components/Modal";
// --- 타입 정의 ---

// 5. react-pageflip 라이브러리의 ref가 노출하는 API 타입
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
  const { t } = useTranslation("viewer");
  const { bookId } = useParams<{ bookId: string }>();
  const location = useLocation();

  const [book, setBook] = useState<BookData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(0);
  const [flipbookSize, setFlipbookSize] = useState({ width: 400, height: 550 });
  const [showShareModal, setShowShareModal] = useState<boolean>(false);
  const [isShared, setIsShared] = useState<boolean>(false);
  const [isTogglingShare, setIsTogglingShare] = useState<boolean>(false);

  const bookRef = useRef<HTMLFlipBookRef | null>(null);
  const navigate = useNavigate();
  const posthog = usePostHog();

  // 공유 페이지 여부 확인
  const isSharedPage = location.pathname.startsWith("/shared/");

  // 공유 링크 생성
  const shareUrl = `${window.location.origin}/shared/${bookId}`;

  useEffect(() => {
    if (!bookId) {
      setIsLoading(false);
      return;
    }

    const fetchBook = async () => {
      try {
        setIsLoading(true);
        setErrorMessage("");
        const data: BookData = await getStorybookById(bookId);
        setBook(data);
        setIsShared(data.is_shared || false); // 초기 공유 상태 설정
        posthog?.capture("book_viewed", {
          book_id: bookId,
          page_count: data.pages?.length || 0,
        });
      } catch (error) {
        setErrorMessage(getUserFriendlyErrorMessage(error));
      } finally {
        setIsLoading(false);
      }
    };

    fetchBook();
  }, [bookId, posthog]);

  // 반응형 플립북 크기 조정
  useEffect(() => {
    const updateFlipbookSize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      // if (width < 1024) {
      if (width < 640) {
        // Mobile - 화면의 70% 활용
        const bookWidth = Math.min(280, width * 0.7);
        const bookHeight = bookWidth * 1.375; // 책 비율 유지
        setFlipbookSize({
          width: bookWidth,
          height: Math.min(bookHeight, height * 0.6),
        });
        // console.log(640);
      } else if (width < 768) {
        // Tablet
        setFlipbookSize({ width: 330, height: 481 });
        // console.log(768);
      } else if (width < 1024) {
        // Small Desktop
        setFlipbookSize({ width: 380, height: 522 });
      } else {
        // Large Desktop
        setFlipbookSize({ width: 420, height: 577 });
      }
    };

    updateFlipbookSize();
    window.addEventListener("resize", updateFlipbookSize);
    return () => window.removeEventListener("resize", updateFlipbookSize);
  }, []);

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

  const handleToggleShare = async () => {
    if (!bookId || isTogglingShare) return;

    try {
      setIsTogglingShare(true);
      const newSharedState = !isShared;

      await toggleBookShare(bookId, newSharedState);
      setIsShared(newSharedState);

      // 공유 상태로 변경했을 때만 모달 표시
      if (newSharedState) {
        setShowShareModal(true);
      }

      posthog?.capture("book_share_toggled", {
        book_id: bookId,
        is_shared: newSharedState,
      });
    } catch (error) {
      console.error("Failed to toggle share:", error);
      // 에러 발생 시 상태 복구는 하지 않음 (API 호출이 실패했으므로)
    } finally {
      setIsTogglingShare(false);
    }
  };

  // Helper to check if url is video
  const isVideo = (url?: string) => {
    if (!url) return false;
    // Presigned URL에는 쿼리 파라미터가 포함되므로 endsWith 대신 includes 사용
    // 또는 URL 객체로 파싱하여 pathname 확인이 더 정확함
    try {
      const urlObj = new URL(url);
      return urlObj.pathname.toLowerCase().endsWith(".mp4");
    } catch {
      // URL 파싱 실패 시 단순 문자열 체크
      return url.toLowerCase().includes(".mp4");
    }
  };

  // Calculate total pages (cover + content pages + back cover)
  const totalPages = book ? book.pages.length * 2 + 2 : 0;

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 md:p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 sm:gap-4">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 sm:h-18 sm:w-18 md:h-20 md:w-20 border-4 border-amber-200 border-t-amber-500"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 sm:h-18 sm:w-18 md:h-20 md:w-20 border-2 border-amber-400/40"></div>
          </div>
          <div className="text-lg sm:text-xl md:text-2xl font-bold text-amber-900 tracking-wide text-center px-4">
            {t("loading")}
          </div>
        </div>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="p-4 sm:p-6 md:p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-6 sm:p-8 max-w-md w-full mx-4 text-center border-2 border-red-200">
          <div className="text-4xl sm:text-5xl md:text-6xl mb-3 sm:mb-4 animate-pulse">
            ⚠️
          </div>
          <div className="text-xl sm:text-2xl font-bold text-red-600 mb-2">
            {t("error")}
          </div>
          <p className="text-sm sm:text-base text-gray-600 mb-4 sm:mb-6">
            {errorMessage}
          </p>
          <button
            onClick={() => navigate("/")}
            className="px-5 sm:px-6 py-2.5 sm:py-3 text-sm sm:text-base bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300"
          >
            {t("backToBookshelf")}
          </button>
        </div>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="p-4 sm:p-6 md:p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-6 sm:p-8 max-w-md w-full mx-4 text-center">
          <div className="text-4xl sm:text-5xl md:text-6xl mb-3 sm:mb-4">
            📚
          </div>
          <div className="text-xl sm:text-2xl font-bold text-amber-900 mb-2">
            {t("notFound")}
          </div>
          <button
            onClick={() => navigate("/")}
            className="mt-3 sm:mt-4 px-5 sm:px-6 py-2.5 sm:py-3 text-sm sm:text-base bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300"
          >
            {t("backToBookshelf")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-4 md:p-6 flex flex-col items-center bg-gradient-to-br from-orange-50 via-amber-50/50 to-orange-50 min-h-full min-w-3xl ">
      {/* Header with title and close button */}
      <div className="relative flex items-center justify-center w-full mb-3 sm:mb-4 md:mb-5 px-2">
        {!isSharedPage && (
          <div className="absolute left-2 sm:left-4 md:left-8 lg:left-10">
            <button
              onClick={handleToggleShare}
              disabled={isTogglingShare}
              className={`
                flex items-center gap-2 px-3 sm:px-4 py-2 sm:py-2.5
                text-xs sm:text-sm font-semibold rounded-full shadow-md
                transition-all duration-300 ease-in-out
                disabled:opacity-50 disabled:cursor-not-allowed
                ${
                  isShared
                    ? "bg-amber-300 text-gray-800 font-semibold px-4 sm:px-5 py-2 sm:py-2.5 text-sm sm:text-base rounded-full shadow-sm hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }
              `}
            >
              <Share2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>
                {isShared ? t("shareToggleOn") : t("shareToggleOff")}
              </span>
            </button>
          </div>
        )}
        <h1 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold text-amber-900 tracking-tight drop-shadow-sm text-center">
          {book.title || t("noTitle")}
        </h1>
        {!isSharedPage && (
          <button
            onClick={() => navigate("/")}
            className="absolute right-1 sm:right-2 md:right-4 lg:right-6 bg-white rounded-full p-2 sm:p-2.5 md:p-3 shadow-xl hover:scale-110 hover:bg-gradient-to-br hover:from-amber-400 hover:to-amber-500 hover:text-white transition-all duration-300 border-2 border-amber-200/50"
          >
            <X className="w-5 h-5 sm:w-6 sm:h-6 md:w-7 md:h-7" />
          </button>
        )}
      </div>

      <HTMLFlipBook
        width={flipbookSize.width}
        height={flipbookSize.height}
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
        usePortrait={false}
        onFlip={(e: number | { data: number }) => {
          const pageNum = typeof e === "object" ? e.data : e;
          setCurrentPage(pageNum);
          posthog?.capture("page_turned", {
            book_id: bookId,
            page_number: pageNum,
          });
        }}
      >
        {/* 첫 번째 페이지: 커버 이미지 */}
        <Page
          className="demoPage border bg-white shadow-2xl/30"
          data-density="hard"
        >
          <img
            src={book.cover_image}
            alt={t("coverAlt")}
            className="w-full h-full object-cover"
          />
        </Page>

        {/* 책 내용 */}
        {book.pages.map((pageData: PageData) => [
          // 이미지 (오른쪽 접힌 부분 효과)
          <Page
            key={`image-${pageData.id}`}
            className="relative bg-white flex flex-col justify-center items-center p-5 shadow-2xl/30 "
          >
            {isVideo(pageData.image_url) ? (
              <video muted autoPlay loop className="h-full w-full object-cover">
                <source src={`${pageData.image_url}`} type="video/mp4" />
              </video>
            ) : (
              <img
                src={`${pageData.image_url}`}
                className="h-full w-full object-cover"
              />
            )}
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
          <Page
            key={`text-${pageData.id}`}
            className="relative w-full h-full bg-white flex flex-col justify-center items-center p-10 shadow-2xl/30 "
          >
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
            <div className=" w-full h-full flex flex-col justify-center items-start">
              {pageData.dialogues.map((dialogue: Dialogue) => (
                <div
                  key={dialogue.id}
                  className="relative w-full mb-5 flex items-center justify-start "
                  onClick={(e: React.MouseEvent) => e.stopPropagation()}
                  onMouseDown={(e: React.MouseEvent) => e.stopPropagation()}
                  onTouchStart={(e: React.TouchEvent) => e.stopPropagation()}
                >
                  <ClickableText
                    text={getDialogueText(dialogue, "en")}
                    book_id={bookId!}
                  />
                  <AudioPlayer
                    src={getDialogueAudioUrl(dialogue, "en") || ""}
                  />
                </div>
              ))}
            </div>
          </Page>,
        ])}

        {/* 마지막 페이지: 뒷면 커버 */}
        <Page
          className="demoPage bg-[#f2bf27] relative w-full min-h-[200px] shadow-2xl/30"
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
      <div className="flex justify-center items-center gap-6 sm:gap-8 md:gap-10 lg:gap-12 mt-3 sm:mt-4 md:mt-5">
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

      {/* 공유 모달 */}
      <ShareModal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        shareUrl={shareUrl}
      />
    </div>
  );
};

export default Viewer;
