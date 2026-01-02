import apiClient from "./client";

export type BookStatus = "creating" | "completed" | "failed" | "draft";
export interface Book {
  id: string;
  title: string;
  cover_image: string;
  status: BookStatus;
  is_default: boolean;
}

// 전체 책 조회
export const getAllStorybooks = async (): Promise<Book[]> => {
  const response = await apiClient.get("/storybook/books");
  return response.data;
};

// 책 상세 내용 조회
export const getStorybookById = async (bookId: string) => {
  if (!bookId) {
    throw new Error("Book ID is required");
  }

  const response = await apiClient.get(`/storybook/books/${bookId}`);
  return response.data;
};

// 책 삭제
export const deleteBook = async (bookId: string) => {
  if (!bookId) {
    throw new Error("Book ID is required");
  }

  const response = await apiClient.delete(`/storybook/books/${bookId}`);
  return response.data;
};

export const getWordTTS = async (word: string, book_id: string) => {
  const response = await apiClient.get(
    `/tts/words/${book_id}/${encodeURIComponent(word)}`
  );
  return response.data;
};

export const getVoices = async () => {
  const response = await apiClient.get("/tts/voices");
  return response.data;
};

// API 응답 타입 정의
interface StorybookResponse {
  id: string;
  url: string;
  message?: string;
}

// 함수 파라미터 타입 정의
interface CreateStorybookParams {
  stories: string[];
  images: File[];
  voice_id?: string | null;
  level: string;
}

export const createStorybook = async ({
  stories,
  images,
  voice_id,
  level,
}: CreateStorybookParams): Promise<StorybookResponse> => {
  const formData = new FormData();

  // stories 배열 추가
  stories.forEach((story: string) => {
    formData.append("stories", story);
  });

  // images 파일 배열 추가
  images.forEach((image: File) => {
    formData.append("images", image);
  });

  if (voice_id) {
    formData.append("voice_id", voice_id);
  }
  if (level) {
    formData.append("level", level);
  }

  const response = await apiClient.post(
    "/storybook/create/with-images",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
};

interface CreateVoiceCloneParams {
  name: string;
  file: File;
  description?: string;
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

  formData.append("name", name.trim());
  formData.append("audio_file", file); // ✅ 백엔드와 일치하도록 'audio_file'로 변경

  if (description) {
    formData.append("description", description);
  }

  // ✅ Content-Type을 명시적으로 제거하여 브라우저가 자동으로 multipart/form-data 설정하도록 함
  const response = await apiClient.post<VoiceCloneResponse>(
    "/tts/voices/clone",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
};

// 책 공유 상태 토글
export const toggleBookShare = async (
  bookId: string,
  isShared: boolean
): Promise<void> => {
  if (!bookId) {
    throw new Error("Book ID is required");
  }

  await apiClient.patch(`/storybook/books/${bookId}/share`, {
    is_shared: isShared,
  });
};

// 미디어 URL 갱신 응답 타입
export interface RefreshMediaUrlsResponse {
  page_id: string;
  urls: {
    video_url?: string;
    image_url?: string;
    audios?: Array<{
      dialogue_id: string;
      language_code: string;
      audio_url: string;
    }>;
  };
  expires_at: string; // ISO 8601 datetime (3시간 후)
}

/**
 * 미디어 URL 갱신 (비공개 콘텐츠 전용)
 *
 * @throws {Error} 400 - 공개 콘텐츠는 갱신 불필요
 * @throws {Error} 403 - 권한 없음
 * @throws {Error} 404 - 책/페이지를 찾을 수 없음
 */
export const refreshMediaUrls = async (
  bookId: string,
  pageId: string
): Promise<RefreshMediaUrlsResponse> => {
  if (!bookId || !pageId) {
    throw new Error("Book ID and Page ID are required");
  }

  const response = await apiClient.post<RefreshMediaUrlsResponse>(
    `/media/books/${bookId}/pages/${pageId}/refresh-urls`
  );
  return response.data;
};
