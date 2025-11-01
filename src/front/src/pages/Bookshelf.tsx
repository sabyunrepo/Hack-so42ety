import { useEffect } from 'react';
import { isDeepStrictEqual } from 'util';

export default function Bookshelf() {
  // 책 목록 불러오기
  useEffect(() => {
    const fetchBooks = async () => {
      // API 호출로 책 목록 가져오기
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
    <div>
      Bookshelf
    </div>
  );
}
