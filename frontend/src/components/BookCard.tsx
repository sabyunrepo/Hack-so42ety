import { X } from "lucide-react";
import type { Book } from "../api";

// Book 타입 정의 (BookCard에서 사용하는 필드들)

// BookCard props 타입
interface BookCardProps {
  book: Book;
  isEditing?: boolean;
  onDelete?: () => void;
  onClick?: () => void;
}

export default function BookCard({
  book,
  isEditing = false,
  onDelete,
  onClick,
}: BookCardProps) {
  const isProcessing = book.status === "creating";
  const isError = book.status === "failed";

  const handleClick = () => {
    // process 또는 error 상태일 때는 클릭 불가
    if (isProcessing || isError) {
      return;
    }
    if (!isEditing && onClick) {
      onClick();
    }
  };

  // 책 상태에 따른 이미지 처리
  const getBookImage = (): string => {
    if (book.status === "completed") {
      return (
        book.cover_image ||
        "https://placehold.co/400x600/f3f4f6/9ca3af?text=No+Image..."
      );
    }
    if (book.status === "failed") {
      return "https://placehold.co/400x600/fef2f2/ef4444?text=생성+실패";
    }
    return (
      book.cover_image ||
      "https://placehold.co/400x600/f3f4f6/9ca3af?text=Creating"
    );
  };

  return (
    <div
      className={`group relative h-[180px] w-[135px] sm:h-[200px] sm:w-[150px] md:h-[228px] md:w-[171px] transition-all duration-300 ${
        isProcessing || isError
          ? "cursor-not-allowed opacity-75"
          : "cursor-pointer hover:scale-105 sm:hover:scale-110 hover:-translate-y-1 sm:hover:-translate-y-2 hover:z-10"
      }`}
      data-name="책장 컴포넌트"
      onClick={handleClick}
    >
      {/* 그림자 효과 */}
      <div className="absolute inset-0 rounded-[13px] shadow-lg group-hover:shadow-2xl transition-shadow duration-300" />

      {/* 책 커버 이미지 */}
      <div className="absolute inset-0 pointer-events-none rounded-[13px] overflow-hidden">
        <img
          alt="책 커버"
          className="absolute inset-0 max-w-none object-cover rounded-[13px] size-full"
          src={getBookImage()}
        />
        {/* 미세한 그라데이션 오버레이 */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/10" />
        <div
          aria-hidden="true"
          className="absolute border-[3px] border-gray-800/30 border-solid inset-0 rounded-[13px]"
        />
      </div>

      {/* 책 제목 배경 (하단 영역) - 글래스모픽 효과 */}
      <div className="absolute bottom-0 left-0 right-0 top-[78.07%] rounded-b-[13px] overflow-hidden bg-white/95 backdrop-blur-sm border-t-[3px] border-gray-800/30 flex items-center justify-center px-1.5 sm:px-2">
        <p className="text-[11px] sm:text-[12px] md:text-[13px] text-gray-900 text-center font-semibold line-clamp-2 break-words leading-snug">
          {book.title}
        </p>
      </div>

      {/* 생성중 오버레이 - 개선된 디자인 */}
      {isProcessing && (
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900 to-gray-800 rounded-[13px] flex flex-col items-center justify-center z-20 pointer-events-none backdrop-blur-sm">
          <div className="relative">
            <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 md:h-14 md:w-14 border-4 border-amber-400/20 border-t-amber-400 mb-3 sm:mb-4"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-10 w-10 sm:h-12 sm:w-12 md:h-14 md:w-14 border-2 border-amber-400/40"></div>
          </div>
          <p className="text-white font-bold text-base sm:text-lg tracking-wide">
            생성중...
          </p>
          <div className="flex gap-1 mt-2">
            <div
              className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-amber-400 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            ></div>
            <div
              className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-amber-400 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            ></div>
            <div
              className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-amber-400 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            ></div>
          </div>
        </div>
      )}

      {/* 에러 오버레이 - 개선된 디자인 */}
      {isError && (
        <div className="absolute inset-0 bg-gradient-to-br from-red-600 to-red-700 rounded-[13px] flex flex-col items-center justify-center z-20 pointer-events-none backdrop-blur-sm">
          <div className="relative mb-2 sm:mb-3">
            <div className="text-white text-4xl sm:text-5xl md:text-6xl drop-shadow-lg animate-pulse">
              ⚠️
            </div>
            <div className="absolute inset-0 blur-xl bg-red-300/30 rounded-full"></div>
          </div>
          <p className="text-white font-bold text-base sm:text-lg md:text-xl tracking-wide drop-shadow-md">
            생성 실패
          </p>
          <p className="text-red-100 text-xs sm:text-sm mt-1.5 sm:mt-2 px-3 sm:px-4 py-1 bg-white/10 rounded-full backdrop-blur-sm">
            삭제 후 재시도
          </p>
        </div>
      )}

      {/* 편집 모드일 때 삭제 버튼 - 세련된 디자인 */}
      {isEditing && !isProcessing && onDelete && !book.is_default && (
        <button
          onClick={onDelete}
          className="absolute -top-2 -right-2 sm:-top-3 sm:-right-3 bg-gradient-to-br from-red-500 to-red-600 text-white rounded-full p-1.5 sm:p-2 hover:from-red-600 hover:to-red-700 hover:scale-110 active:scale-95 transition-all duration-200 shadow-lg hover:shadow-xl z-10 border-2 border-white"
        >
          <X className="w-4 h-4 sm:w-5 sm:h-5" />
        </button>
      )}
    </div>
  );
}

// Book 타입을 외부에서도 사용할 수 있도록 export
export type { Book, BookCardProps };
