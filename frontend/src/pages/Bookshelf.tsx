import { Link, useNavigate } from "react-router-dom";
import BookCard, { type Book } from "../components/BookCard";
import { useEffect, useState, useMemo } from "react"; // useMemo 추가
import { deleteBook, getAllStorybooks } from "../api/index";
import { ConfirmModal } from "../components/Modal";
import { getUserFriendlyErrorMessage } from "../utils/errorHandler";
import { usePostHog } from "@posthog/react";
import { useTranslation } from "react-i18next";

/**
 * 화면 너비에 따라 선반당 표시할 책의 컬럼 수를 반환합니다.
 * Tailwind CSS의 기본 breakpoint를 사용합니다:
 * - sm (640px): 3개 컬럼
 * - md (768px): 4개 컬럼
 * - 기본값: 2개 컬럼
 */
const useResponsiveColumns = () => {
  const [columns, setColumns] = useState(2); // 기본값: 2개

  useEffect(() => {
    // 현재 너비에 따른 컬럼 수를 계산하는 함수
    const calculateColumns = () => {
      const width = window.innerWidth;
      if (width >= 1024) {
        // md (768px 이상)
        setColumns(4);
      } else if (width >= 640) {
        // sm (640px 이상)
        setColumns(3);
      } else {
        // 기본
        setColumns(2);
      }
    };

    // 초기 로드 시 계산
    calculateColumns();

    // 리사이즈 이벤트 리스너 추가
    window.addEventListener("resize", calculateColumns);

    // 컴포넌트 언마운트 시 리스너 제거
    return () => {
      window.removeEventListener("resize", calculateColumns);
    };
  }, []);

  return columns;
};

// 📚 책과 생성 버튼을 포함해서 지정된 컬럼 수로 그룹으로 나누는 함수
// columnsPerShelf 인자를 추가했습니다.
const groupBooksIntoShelves = (
  books: Book[],
  columnsPerShelf: number
): Book[][] => {
  const totalItems = books.length + 1; // 책 + 생성 버튼
  const shelves: Book[][] = [];
  for (let i = 0; i < totalItems; i += columnsPerShelf) {
    // slice의 두 번째 인자는 (i + columnsPerShelf)로 유지합니다.
    // 그룹화할 때 배열 인덱스가 columnsPerShelf를 넘어가도 상관없습니다.
    shelves.push(books.slice(i, i + columnsPerShelf));
  }
  return shelves;
};

export default function Bookshelf() {
  const { t } = useTranslation("bookshelf");
  const navigate = useNavigate();
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [bookToDelete, setBookToDelete] = useState<string | null>(null);
  const posthog = usePostHog();

  // ⭐️ 새로 추가된 반응형 컬럼 수
  const columnsPerShelf = useResponsiveColumns();

  // 책 목록 불러오기
  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setIsLoading(true);
        const data = await getAllStorybooks();
        setBooks(data);
        setError(null);
      } catch (err) {
        setError(getUserFriendlyErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
    };

    fetchBooks();
  }, []);

  // 책 클릭 핸들러
  const handleBookClick = (bookId: string) => {
    navigate(`/book/${bookId}`);
  };

  // 책 삭제 핸들러
  const handleDeleteBook = (bookId: string) => {
    setBookToDelete(bookId);
    setShowConfirmModal(true);
  };

  const confirmDeleteBook = async () => {
    if (!bookToDelete) return;
    const previous = books;
    setBooks((prev) => prev.filter((book) => book.id !== bookToDelete));
    try {
      await deleteBook(bookToDelete);
      posthog?.capture("book_deleted", { book_id: bookToDelete });
    } catch (err) {
      setError(getUserFriendlyErrorMessage(err));
      setBooks(previous);
    }
    setShowConfirmModal(false); // 모달 닫기 추가
  };

  // ⭐️ columnsPerShelf가 변경될 때마다 bookShelves를 다시 계산
  const bookShelves = useMemo(
    () => groupBooksIntoShelves(books, columnsPerShelf),
    [books, columnsPerShelf]
  );

  // ... (로딩/에러 상태 UI는 그대로 유지) ...
  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 md:p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 sm:gap-4">
          <div className="relative">
            <div className="animate-spin rounded-full h-12 w-12 sm:h-14 sm:w-14 md:h-16 md:w-16 border-4 border-amber-200 border-t-amber-500"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-12 w-12 sm:h-14 sm:w-14 md:h-16 md:w-16 border-2 border-amber-400/40"></div>
          </div>
          <div className="text-lg sm:text-xl md:text-2xl font-bold text-amber-900 tracking-wide">
            {t("loading")}
          </div>
          <div className="flex gap-2">
            <div
              className="w-2 h-2 sm:w-3 sm:h-3 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            ></div>
            <div
              className="w-2 h-2 sm:w-3 sm:h-3 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            ></div>
            <div
              className="w-2 h-2 sm:w-3 sm:h-3 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            ></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 md:p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-6 sm:p-8 max-w-md mx-4 text-center border-2 border-red-200">
          <div className="text-4xl sm:text-5xl md:text-6xl mb-4 animate-pulse">
            ⚠️
          </div>
          <div className="text-xl sm:text-2xl font-bold text-red-600 mb-2">
            {error}
          </div>
          <p className="text-sm sm:text-base text-gray-600">{t("error")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 md:p-8 bg-gradient-to-br from-orange-50 via-amber-50/50 to-orange-50 h-full">
      {/* 헤더 영역 */}
      <div className="flex justify-between items-center mb-4 sm:mb-6 md:mb-8">
        <div>
          <p className="text-sm sm:text-base text-amber-700 mt-2">
            {/* [ ] 5권 제한  */}
            {t("remainingCreations", { count: 5 - books.length })}
          </p>
        </div>
        {/* 편집 모드 버튼 (주석 처리됨) */}
        {/* <div>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="bg-amber-300 text-gray-800 font-semibold px-4 sm:px-5 py-2 sm:py-2.5 text-sm sm:text-base rounded-full shadow-sm hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto"
            >
              {isSubmitting ? t("creating") : t("creationComplete")}

            </button>
        </div> */}
      </div>

      {/* 책장 영역 */}
      <div className="space-y-8 sm:space-y-10 md:space-y-12">
        {bookShelves.map((shelf, shelfIndex) => {
          // 마지막 선반인지 확인
          const isLastShelf = shelfIndex === bookShelves.length - 1;
          // 이 선반에 포함되어야 할 '새 책 만들기' 버튼의 자리
          const remainingSpotsInLastShelf = columnsPerShelf - shelf.length;

          return (
            <div key={shelfIndex} className="relative">
              {/* 책 그리드 */}
              {/* ⭐️ Tailwind CSS 클래스는 그대로 두어 Grid 레이아웃을 처리합니다. */}
              {/* groupBooksIntoShelves 로직이 선반당 책의 개수를 조절하고, Tailwind 클래스는 화면 크기에 따라 Grid 컬럼을 시각적으로 조절합니다. */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4 md:gap-6 w-full justify-items-center mb-2 px-2 sm:px-4">
                {shelf.map((book) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    onDelete={() => handleDeleteBook(book.id)}
                    onClick={() => handleBookClick(book.id)}
                  />
                ))}
                {/* [ ] 최대 5개까지만 생성하도록 수정 */}
                {/* 새 책 추가 버튼 (마지막 선반에만 표시) */}
                {isLastShelf && books.length < 5 && (
                  <Link to="/create" className="group">
                    <div className="h-[180px] w-[135px] sm:h-[200px] sm:w-[150px] md:h-[228px] md:w-[171px] border-[3px] border-dashed border-amber-400/50 rounded-[13px] flex items-center justify-center bg-white/40 backdrop-blur-sm hover:bg-amber-50/60 hover:border-amber-500 transition-all duration-300 shadow-md hover:shadow-xl hover:scale-105 cursor-pointer">
                      <div className="text-center">
                        <div className="text-4xl sm:text-5xl md:text-6xl mb-2 text-amber-500 group-hover:text-amber-600 transition-colors group-hover:scale-110 transform duration-300">
                          +
                        </div>
                        <p className="text-xs sm:text-sm font-semibold text-amber-700 group-hover:text-amber-800">
                          {t("createBook")}
                        </p>
                      </div>
                    </div>
                  </Link>
                )}

                {/* ⭐️ 마지막 선반에서 빈 공간 채우기 (선택 사항: 버튼 외 빈 칸을 채워 균형을 맞추기 위함) */}
                {isLastShelf &&
                  remainingSpotsInLastShelf > 0 &&
                  [...Array(remainingSpotsInLastShelf - 1)].map((_, i) => (
                    <div
                      key={`spacer-${i}`}
                      // 빈 공간의 크기를 BookCard와 동일하게 설정하여 그리드 균형을 맞춥니다.
                      className="h-[180px] w-[135px] sm:h-[200px] sm:w-[150px] md:h-[228px] md:w-[171px] invisible"
                    ></div>
                  ))}
              </div>

              {/* 선반 - 개선된 3D 효과 (기존 코드와 동일) */}
              <div
                className="w-full h-6 sm:h-7 md:h-8 rounded-lg shadow-2xl relative overflow-hidden mt-2"
                style={{ backgroundColor: "#A0826D" }}
              >
                {/* 상단 하이라이트 */}
                <div className="absolute top-0 left-0 right-0 h-1 sm:h-1.5 md:h-2 bg-gradient-to-b from-white/40 to-transparent"></div>
                {/* 하단 그림자 */}
                <div className="absolute bottom-0 left-0 right-0 h-2 sm:h-2.5 md:h-3 bg-gradient-to-t from-black/30 to-transparent"></div>
                {/* 좌측 그림자 */}
                <div className="absolute top-0 bottom-0 left-0 w-2 sm:w-2.5 md:w-3 bg-gradient-to-r from-black/20 to-transparent"></div>
                {/* 우측 하이라이트 */}
                <div className="absolute top-0 bottom-0 right-0 w-2 sm:w-2.5 md:w-3 bg-gradient-to-l from-white/10 to-transparent"></div>
                {/* 나무 질감 효과 */}
                <div
                  className="absolute inset-0 opacity-10"
                  style={{
                    backgroundImage:
                      "repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.1) 2px, rgba(0,0,0,0.1) 4px)",
                  }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 빈 상태 메시지 (기존 코드와 동일) */}
      {books.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 sm:py-16 md:py-20 px-4">
          <div className="text-5xl sm:text-6xl md:text-8xl mb-4 sm:mb-5 md:mb-6 opacity-50">
            📚
          </div>
          <h2 className="text-2xl sm:text-2xl md:text-3xl font-bold text-amber-800 mb-2 sm:mb-3 text-center">
            {t("emptyTitle")}
          </h2>
          <p className="text-sm sm:text-base text-amber-600 mb-4 sm:mb-5 md:mb-6 text-center">
            {t("emptySubtitle")}
          </p>
          <Link to="/create">
            <button className="px-6 sm:px-7 md:px-8 py-3 sm:py-3.5 md:py-4 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300 text-sm sm:text-base">
              + {t("createBook")}
            </button>
          </Link>
        </div>
      )}

      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title={t("deleteBook")}
        message={t("deleteConfirm")}
        onConfirm={() => confirmDeleteBook()}
      />
    </div>
  );
}
