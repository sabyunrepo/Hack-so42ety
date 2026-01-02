/**
 * Book Types - Multi-language support
 * 동화책 타입 정의 (다국어 지원)
 */

// ==================== Multi-Language Support Types ====================

/**
 * 대화문 번역
 */
export interface DialogueTranslation {
  language_code: string; // ISO 639-1 (en, ko, ja, zh, etc.)
  text: string;
  is_primary: boolean; // 원본 언어 여부
}

/**
 * 대화문 오디오
 */
export interface DialogueAudio {
  language_code: string; // ISO 639-1 (en, ko, ja, zh, etc.)
  voice_id: string; // ElevenLabs voice ID
  audio_url: string;
  duration?: number; // 재생 시간 (초)
}

/**
 * 대화문 (다국어 지원)
 */
export interface Dialogue {
  id: string;
  sequence: number;
  speaker: string;
  translations: DialogueTranslation[];
  audios: DialogueAudio[];

  // DEPRECATED: 하위 호환성을 위한 필드
  text_en?: string;
  text_ko?: string;
  audio_url?: string;
}

/**
 * 페이지
 */
export interface PageData {
  id: string;
  sequence: number;
  image_url?: string;
  image_prompt?: string;
  dialogues: Dialogue[];
  video_url?: string; // 비디오 URL (있는 경우)
  expires_at?: string; // URL 만료 시간 (ISO 8601, 비공개 콘텐츠)
}

/**
 * 동화책
 */
export interface BookData {
  id: string;
  title: string;
  cover_image?: string;
  status: string;
  created_at: string;
  pages: PageData[];
  is_shared?: boolean; // 공유 상태
}

/**
 * 동화책 목록 응답
 */
export interface BookListResponse {
  books: BookData[];
}

// ==================== Helper Functions ====================

/**
 * 특정 언어의 번역 텍스트 가져오기
 */
export function getTranslationText(
  dialogue: Dialogue,
  languageCode: string
): string | undefined {
  const translation = dialogue.translations.find(
    (t) => t.language_code === languageCode
  );
  return translation?.text;
}

/**
 * 원본 언어의 번역 텍스트 가져오기
 */
export function getPrimaryTranslation(
  dialogue: Dialogue
): DialogueTranslation | undefined {
  return dialogue.translations.find((t) => t.is_primary);
}

/**
 * 특정 언어의 오디오 가져오기
 */
export function getAudioUrl(
  dialogue: Dialogue,
  languageCode: string
): string | undefined {
  const audio = dialogue.audios.find((a) => a.language_code === languageCode);
  return audio?.audio_url;
}

/**
 * 하위 호환성: deprecated 필드 또는 새 필드에서 텍스트 가져오기
 */
export function getDialogueText(
  dialogue: Dialogue,
  languageCode: string = "en"
): string {
  // 새 구조에서 시도
  const translationText = getTranslationText(dialogue, languageCode);
  if (translationText) return translationText;

  // DEPRECATED 필드에서 시도 (하위 호환성)
  if (languageCode === "en" && dialogue.text_en) return dialogue.text_en;
  if (languageCode === "ko" && dialogue.text_ko) return dialogue.text_ko;

  // 원본 언어 텍스트 반환
  const primary = getPrimaryTranslation(dialogue);
  return primary?.text || "";
}

/**
 * 하위 호환성: deprecated 필드 또는 새 필드에서 오디오 URL 가져오기
 */
export function getDialogueAudioUrl(
  dialogue: Dialogue,
  languageCode: string = "en"
): string | undefined {
  // 새 구조에서 시도
  const audioUrl = getAudioUrl(dialogue, languageCode);
  if (audioUrl) return audioUrl;

  // DEPRECATED 필드에서 시도 (하위 호환성)
  return dialogue.audio_url;
}
