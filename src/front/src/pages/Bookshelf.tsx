import { useEffect, useState } from 'react';
import { getAllStorybooks } from '../api/index';
import BookCard from "../components/BookCard";

// 일단 간단한 타입으로 시작
interface Book {
  id: string;
  title?: string;
  cover_image?: string;
  status?: string;
  // 나머지는 any로 허용
  [key: string]: any;
}

interface ApiResponse {
  books: Book[];
  [key: string]: any; // 유연하게 시작
}

export default function Bookshelf() {
  const [isEditing, setIsEditing] = useState(false);
  const [books, setBooks] = useState<Book[]>([]);

  // 책 목록 불러오기
  useEffect(() => {
    const fetchBooks = async () => {
      try {
        const data = await getAllStorybooks() as ApiResponse;
        setBooks(data.books || []);
        console.log(data);
      } catch (error) {
        console.error('Failed to fetch books:', error);
        setBooks([]);
      }
    };
    fetchBooks();
  }, []);

  //책 클릭 핸들러
  const handleBookClick = (bookId: string) => {
    // 뷰어 페이지로 이동
  }

  //책 삭제 핸들러
  const handleDeleteBook = (bookId: string) => {
    // 책 삭제 로직
  }

  // 편집 모드 토글
  const toggleEditMode = () => {
    // 편집 모드 토글 로직
  }

  // 책과 생성 버튼을 포함해서 4개씩 그룹으로 나누는 함수
  const groupBooksIntoShelves = (books: Book[]): Book[][] => {
    const  totalItems = books.length + 1; // 책 + 생성 버튼
    const shelves: Book[][] = [];
    for (let i = 0; i < totalItems; i += 4) {
      shelves.push(books.slice(i, i + 4));
    }
    return shelves;
  }

  const bookShelves = groupBooksIntoShelves(books);

  return (
    <div className="p-8 bg-orange-50 min-h-screen">
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
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
