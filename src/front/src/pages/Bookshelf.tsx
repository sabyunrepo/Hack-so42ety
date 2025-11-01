import { Link, useNavigate } from "react-router-dom";
import BookCard, { type Book } from "../components/BookCard";
import { useEffect, useState } from "react";
import { deleteBook, getAllStorybooks } from "../api/index";

export default function Bookshelf() {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [books, setBooks] = useState<Book[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 책 목록 불러오기
  useEffect(() => {
    const fetchBooks = async () => {
      try {
        setIsLoading(true);
        const data = await getAllStorybooks();
        setBooks(data.books);
        console.log(data);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch books:", err);
        setError("책 목록을 불러오는데 실패했습니다.");
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
  const handleDeleteBook = async (bookId: string) => {
    if (window.confirm("정말로 이 책을 삭제하시겠습니까?")) {
      const previous = books;
      setBooks((prev) => prev.filter((book) => book.id !== bookId));
      try {
        // await deleteBook(bookId);
        alert("책 삭제에 성공했습니다.");
      } catch (err) {
        console.error("Failed to delete book:", err);
        setBooks(previous);
        alert("책 삭제에 실패했습니다.");
      }
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
      <div className="p-8 bg-orange-50 min-h-screen flex items-center justify-center">
        <div className="text-xl font-medium">책장을 불러오는 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-orange-50 min-h-screen flex items-center justify-center">
        <div className="text-xl font-medium text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-orange-50 min-h-screen">
      <div className="flex justify-end mb-6">
        <button
          onClick={toggleEditMode}
          className="bg-amber-300 text-gray-800 font-semibold px-5 py-2 rounded-full shadow-sm hover:bg-amber-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isEditing ? "편집 완료" : "편집"}
        </button>
      </div>
      <div className="space-y-8">
        {bookShelves.map((shelf, shelfIndex) => (
          <div key={shelfIndex} className="relative">
            <div className="grid grid-cols-4 gap-1 w-full justify-items-center mb-0">
              {shelf.map((book) => (
                <BookCard
                  key={book.id}
                  book={book}
                  isEditing={isEditing}
                  onDelete={() => handleDeleteBook(book.id)}
                  onClick={() => handleBookClick(book.id)}
                />
              ))}
              {shelfIndex === bookShelves.length - 1 && (
                <Link to="/create">
                  <div className="h-[228px] w-[171px] border-3 border-black border-dashed rounded-[13px] flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-4xl mb-2">+</div>
                    </div>
                  </div>
                </Link>
              )}
            </div>

            {/* 선반 */}
            <div
              className="w-full h-6 rounded-lg shadow-lg relative overflow-hidden"
              style={{ backgroundColor: "#C1A78E" }}
            >
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white to-transparent opacity-30"></div>
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-black to-transparent opacity-20"></div>
              <div className="absolute top-0 bottom-0 left-0 w-1 bg-gradient-to-b from-transparent via-black to-transparent opacity-15"></div>
              <div className="absolute top-0 bottom-0 right-0 w-1 bg-gradient-to-b from-transparent via-black to-transparent opacity-15"></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
