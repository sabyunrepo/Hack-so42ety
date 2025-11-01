// src/pages/Viewer.tsx
import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import HTMLFlipBook from "react-pageflip";
import { X } from "lucide-react";
import MoriAI_Icon from "../assets/MoriAI_Icon.svg";

// 1. API 함수와 컴포넌트 임포트
// A_TODO: 'api/index' 파일이 .ts로 변환되었는지, getStorybookById 함수가
// Promise<BookData>를 반환하도록 타입이 지정되었는지 확인하세요.
import { getStorybookById } from "../api/index";
// import AudioPlayer from "../components/AudioPlayer";
// import ClickableText from "../components/ClickableText";

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
    }
  };

  const handlePrevPage = () => {
    if (bookRef.current) {
      bookRef.current.pageFlip().flipPrev();
    }
  };

  if (isLoading) {
    return <div className="p-8">스토리북을 불러오는 중...</div>;
  }

  if (isError) {
    return <div className="p-8">오류가 발생했습니다.</div>;
  }

  // 10. book 객체가 null이 아님을 TypeScript에 확인
  if (!book) {
    return <div className="p-8">스토리북 데이터를 찾을 수 없습니다.</div>;
  }

  return (
    <div className="p-7 bg-orange-50 flex flex-col justify-center items-center ">
      <div className="relative flex items-center justify-center w-full mb-3">
        <h1 className="text-3xl font-bold mb-4">{book.title || "제목 없음"}</h1>
        <button
          onClick={() => navigate("/")}
          className="absolute right-8 bg-white rounded-full p-3.5 shadow-xl hover:scale-110 hover:bg-yellow-400 hover:text-white transition-all"
        >
          <X className="w-8 h-8" />
        </button>
      </div>
      <div className="w-full flex justify-center">
        <div className="w-full max-w-[420px] md:max-w-[520px]"></div>
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
        disableFlipByClick={false}
        clickEventForward={false}
        size="fixed"
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
                {/* <ClickableText text={dialogue.text} book_id={bookId!} />
                <AudioPlayer src={`${dialogue.part_audio_url}`} /> */}
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
      <div className=" w-full flex justify-around items-center">
        {/* ... 버튼들 ... */}
        <button
          onClick={handlePrevPage}
          className=" m-1 bg-white rounded-full p-3.5 shadow-xl hover:scale-110 hover:bg-yellow-400 hover:text-white transition-all"
        >
          <svg
            className="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
        <button
          onClick={handleNextPage}
          className="  bg-white rounded-full p-3.5 shadow-xl hover:scale-110 hover:bg-yellow-400 hover:text-white transition-all"
        >
          <svg
            className="w-8 h-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default Viewer;
