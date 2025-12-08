import { Link, useNavigate } from "react-router-dom";
import BookCard, { type Book } from "../components/BookCard";
import { useEffect, useState } from "react";
import { deleteBook, getAllStorybooks } from "../api/index";
import { ConfirmModal } from "../components/Modal";
import { getUserFriendlyErrorMessage } from "../utils/errorHandler";

export default function Bookshelf() {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [bookToDelete, setBookToDelete] = useState<string | null>(null);

  // 책 목록 불러오기
  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setIsLoading(true);
        const data = await getAllStorybooks();
        setBooks(data);
        console.log(data);
        setError(null);
      } catch (err) {
        setError(getUserFriendlyErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
    };

    fetchBooks();
  }, []);

  //책 클릭 핸들러
  const handleBookClick = (bookId: string) => {
    if (!isEditing) {
      navigate(`/book/${bookId}`);
    }
  };

  //책 삭제 핸들러
  const handleDeleteBook = (bookId: string) => {
    setBookToDelete(bookId); // 삭제할 책 ID 저장
    setShowConfirmModal(true); // 모달 표시
  };

  const confirmDeleteBook = async () => {
    if (!bookToDelete) return;
    const previous = books;
    setBooks((prev) => prev.filter((book) => book.id !== bookToDelete));
    try {
      await deleteBook(bookToDelete);
    } catch (err) {
      setError(getUserFriendlyErrorMessage(err));
      setBooks(previous);
    }
  };

  // 편집 모드 토글
  const toggleEditMode = () => {
    setIsEditing(!isEditing);
  };

  // 책과 생성 버튼을 포함해서 4개씩 그룹으로 나누는 함수
  const groupBooksIntoShelves = (books: Book[]): Book[][] => {
    const totalItems = books.length + 1; // 책 + 생성 버튼
    const shelves: Book[][] = [];
    for (let i = 0; i < totalItems; i += 4) {
      shelves.push(books.slice(i, i + 4));
    }
    return shelves;
  };

  const bookShelves = groupBooksIntoShelves(books);

  if (isLoading) {
    return (
      <div className="p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-amber-200 border-t-amber-500"></div>
            <div className="absolute inset-0 animate-ping rounded-full h-16 w-16 border-2 border-amber-400/40"></div>
          </div>
          <div className="text-2xl font-bold text-amber-900 tracking-wide">
            책장을 불러오는 중...
          </div>
          <div className="flex gap-2">
            <div
              className="w-3 h-3 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            ></div>
            <div
              className="w-3 h-3 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            ></div>
            <div
              className="w-3 h-3 bg-amber-500 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            ></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-gradient-to-br from-orange-50 to-amber-50 h-full flex items-center justify-center">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-2xl p-8 max-w-md text-center border-2 border-red-200">
          <div className="text-6xl mb-4 animate-pulse">⚠️</div>
          <div className="text-2xl font-bold text-red-600 mb-2">{error}</div>
          <p className="text-gray-600">잠시 후 다시 시도해주세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gradient-to-br from-orange-50 via-amber-50/50 to-orange-50 h-full">
      {/* 헤더 영역 */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <p className="text-amber-700 mt-2">총 {books.length}권의 책</p>
        </div>
        <button
          onClick={toggleEditMode}
          className={`px-6 py-3 rounded-full font-bold shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 active:scale-95 ${
            isEditing
              ? "bg-gradient-to-r from-green-500 to-green-600 text-white hover:from-green-600 hover:to-green-700"
              : "bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 hover:from-amber-500 hover:to-amber-600"
          }`}
        >
          {isEditing ? "✓ 편집 완료" : "✎ 편집"}
        </button>
      </div>

      {/* 책장 영역 */}
      <div className="space-y-12">
        {bookShelves.map((shelf, shelfIndex) => (
          <div key={shelfIndex} className="relative">
            {/* 책 그리드 */}
            <div className="grid grid-cols-4 gap-6 w-full justify-items-center mb-2 px-4">
              {shelf.map((book) => (
                <BookCard
                  key={book.id}
                  book={book}
                  isEditing={isEditing}
                  onDelete={() => handleDeleteBook(book.id)}
                  onClick={() => handleBookClick(book.id)}
                />
              ))}
              {/* 새 책 추가 버튼 */}
              {shelfIndex === bookShelves.length - 1 && (
                <Link to="/create" className="group">
                  <div className="h-[228px] w-[171px] border-[3px] border-dashed border-amber-400/50 rounded-[13px] flex items-center justify-center bg-white/40 backdrop-blur-sm hover:bg-amber-50/60 hover:border-amber-500 transition-all duration-300 shadow-md hover:shadow-xl hover:scale-105 cursor-pointer">
                    <div className="text-center">
                      <div className="text-6xl mb-2 text-amber-500 group-hover:text-amber-600 transition-colors group-hover:scale-110 transform duration-300">
                        +
                      </div>
                      <p className="text-sm font-semibold text-amber-700 group-hover:text-amber-800">
                        새 책 만들기
                      </p>
                    </div>
                  </div>
                </Link>
              )}
            </div>

            {/* 선반 - 개선된 3D 효과 */}
            <div
              className="w-full h-8 rounded-lg shadow-2xl relative overflow-hidden mt-2"
              style={{ backgroundColor: "#A0826D" }}
            >
              {/* 상단 하이라이트 */}
              <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-b from-white/40 to-transparent"></div>
              {/* 하단 그림자 */}
              <div className="absolute bottom-0 left-0 right-0 h-3 bg-gradient-to-t from-black/30 to-transparent"></div>
              {/* 좌측 그림자 */}
              <div className="absolute top-0 bottom-0 left-0 w-3 bg-gradient-to-r from-black/20 to-transparent"></div>
              {/* 우측 하이라이트 */}
              <div className="absolute top-0 bottom-0 right-0 w-3 bg-gradient-to-l from-white/10 to-transparent"></div>
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
        ))}
      </div>

      {/* 빈 상태 메시지 */}
      {books.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="text-8xl mb-6 opacity-50">📚</div>
          <h2 className="text-3xl font-bold text-amber-800 mb-3">
            아직 책이 없습니다
          </h2>
          <p className="text-amber-600 mb-6">첫 번째 동화책을 만들어보세요!</p>
          <Link to="/create">
            <button className="px-8 py-4 bg-gradient-to-r from-amber-400 to-amber-500 text-gray-900 font-bold rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300">
              + 새 책 만들기
            </button>
          </Link>
        </div>
      )}

      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="삭제 하시겠습니까?"
        onConfirm={() => confirmDeleteBook()}
      />
    </div>
  );
}
