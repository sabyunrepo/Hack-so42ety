import apiClient from "./client";

export type BookStatus = "process" | "success" | "error";
export interface Book {
  id: string;
  title: string;
  cover_image: string;
  status: BookStatus;
}

interface AllStorybooksResponse {
  books: Book[];
}

// 전체 책 조회
export const getAllStorybooks = async (): Promise<AllStorybooksResponse> => {
  try {
    const response = await apiClient.get("/storybook/books");

    return response.data; // 성공 시 응답 데이터(JSON) 반환
  } catch (error) {
    // API 요청 실패 시 에러 처리
    console.error("Error fetching storybooks:", error);
    // 에러를 다시 throw하여, 이 함수를 호출한 컴포넌트에서도 에러를 처리할 수 있게 함
    throw error;
  }
};

// 책 상세 내용 조회
export const getStorybookById = async (bookId: string) => {
  if (!bookId) {
    throw new Error("Book ID is required");
  }

  try {
    const response = await apiClient.get(`/storybook/books/${bookId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching storybook ${bookId}:`, error);
    throw error;
  }
};

// 책 삭제
export const deleteBook = async (bookId: string) => {
  if (!bookId) {
    throw new Error("Book ID is required");
  }
  try {
    const response = await apiClient.delete(`/storybook/books/${bookId}`);
    console.log(response);
  } catch (error) {
    console.error(`Error deleting storybook ${bookId}:`, error);
    throw error;
  }
};

export const getWordTTS = async (word: string, book_id: string) => {
  try {
    console.log(word, book_id);
    const response = await apiClient.get(
      `/tts/word/generate/${book_id}/${encodeURIComponent(word)}`
    );
    return response.data;
  } catch (error) {
    console.error(error);
    throw error;
  }
};

export const getVoices = async () => {
  try {
    const response = await apiClient.get("/tts/voices");
    return response.data;
  } catch (error) {
    console.error("Error getVoices:", error);
    throw error;
  }
};

// 1. API가 반환하는 데이터 타입을 정의합니다.
// A_TODO: 실제 응답 데이터 구조에 맞게 수정하세요.
interface StorybookResponse {
  id: string;
  url: string;
  message?: string;
}

// 2. 함수에 전달될 파라미터 객체의 타입을 정의합니다.
interface CreateStorybookParams {
  stories: string[];
  images: File[]; // 'images'는 파일 객체이므로 'File[]'로 가정합니다.
  voice_id?: string | null;
}

export const createStorybook = async ({
  stories,
  images,
  voice_id,
}: CreateStorybookParams): Promise<StorybookResponse> => {
  // FormData 생성

  const formData = new FormData();

  // stories 배열 추가 (같은 키로 반복 전송)
  stories.forEach((story: string) => {
    formData.append("stories", story);
  });

  // images 파일 배열 추가 (같은 키로 반복 전송)
  images.forEach((image: File) => {
    formData.append("images", image);
  });

  if (voice_id) {
    formData.append("voice_id", voice_id);
  }

  try {
    console.log("스토리", stories);
    console.log("이미지", images);
    console.log("보이스 아이디", voice_id);
    const response = await apiClient.post("/storybook/create", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    console.error("동화책 생성 실패:", error);
    throw error;
  }
};

interface CreateVoiceCloneParams {
  name: string;
  file: File;
  description?: string; // API 문서에 있는 선택적 파라미터
}

interface VoiceCloneResponse {
  detail: string;
}
export const createVoiceClone = async ({
  name,
  file,
  description,
}: CreateVoiceCloneParams): Promise<VoiceCloneResponse> => {

  const formData = new FormData();

  // 필수 값 추가
  formData.append("name", name.trim());
  formData.append("file", file);

  // 선택적 파라미터 추가
  if (description) {
    formData.append("description", description);
  }

  // Axios를 사용하면 non-2xx 응답은 자동으로 에러를 throw 합니다.
  // 따라서 try/catch는 이 함수를 '호출하는' 곳(handleSubmit)에서 처리합니다.
  const response = await apiClient.post<VoiceCloneResponse>("/tts/clone/create", formData, {
    headers: {
      // 'multipart/form-data'는 브라우저가 FormData와 함께 자동으로 설정해줍니다.
      // (명시적으로 적어도 문제는 없습니다.)
      "Content-Type": "multipart/form-data",
    },
  });

  // 성공 시 (201 Created) response.data를 반환합니다.
  return response.data;
};
