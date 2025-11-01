import { X } from "lucide-react";

// Book 타입 정의 (BookCard에서 사용하는 필드들)
interface Book {
  id: string;
  title: string;
  cover_image?: string;
  status?: "success" | "process" | "error";
}

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
  const isProcessing = book.status === "process";
  const isError = book.status === "error";

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
    if (book.status === "process") {
      return (
        book.cover_image ||
        "https://placehold.co/400x600/f3f4f6/9ca3af?text=생성+중..."
      );
    }
    if (book.status === "error") {
      return "https://placehold.co/400x600/fef2f2/ef4444?text=생성+실패";
    }
    console.log(book.cover_image);

    return (
      book.cover_image ||
      "https://placehold.co/400x600/22c55e/ffffff?text=No+Image"
    );
  };

  return (
    <div
      className={`relative h-[228px] w-[171px] transition-transform ${
        isProcessing || isError
          ? "cursor-not-allowed opacity-75"
          : "cursor-pointer hover:scale-105 hover:z-10"
      }`}
      data-name="책장 컴포넌트"
      onClick={handleClick}
    >
      {/* 책 커버 이미지 */}
      <div className="absolute inset-0 pointer-events-none rounded-[13px]">
        <img
          alt="책 커버"
          className="absolute inset-0 max-w-none object-cover rounded-[13px] size-full"
          src={getBookImage()}
        />
        <div
          aria-hidden="true"
          className="absolute border-[2px] border-black border-solid inset-0 rounded-[13px]"
        />
      </div>
      {/* 책 제목 배경 (하단 흰색 영역) */}
      <div className="absolute bottom-0 left-0 right-0 top-[78.07%] rounded-b-[13px]">
        <div className="w-full h-full bg-white border-[2px] border-black rounded-b-[13px]" />
      </div>

      {/* 책 제목 */}
      <div className="absolute flex flex-col font-normal inset-[82.89%_8.77%_5.26%_8.77%] justify-center items-center text-[12px] text-black text-center leading-tight px-1">
        <p className="line-clamp-2 text-center wrap-break-word overflow-hidden">
          {book.title}
        </p>
      </div>

      {/* 생성중 오버레이 */}
      {isProcessing && (
        <div className="absolute inset-0 bg-black opacity-90 rounded-[13px] flex flex-col items-center justify-center z-20 pointer-events-none">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-white border-t-transparent mb-3 "></div>
          <p className="text-white font-bold text-lg">생성중...</p>
        </div>
      )}

      {/* 에러 오버레이 */}
      {isError && (
        <div className="absolute inset-0 bg-red-600 opacity-90 rounded-[13px] flex flex-col items-center justify-center z-20 pointer-events-none">
          <div className="text-white text-5xl mb-2">⚠️</div>
          <p className="text-white font-bold text-lg">생성 실패</p>
          <p className="text-white text-xs mt-1">삭제 후 재시도</p>
        </div>
      )}

      {/* 편집 모드일 때 삭제 버튼 (생성중이 아닐 때만) */}
      {isEditing && !isProcessing && onDelete && (
        <button
          onClick={onDelete}
          className="absolute -top-2 -right-2 border-[2px] bg-white text-black rounded-full p-1 hover:bg-red-600 transition-colors z-10"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// Book 타입을 외부에서도 사용할 수 있도록 export
export type { Book, BookCardProps };
