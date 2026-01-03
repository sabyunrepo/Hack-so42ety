import React from "react";
import ClickableText from "../ClickableText";
import AudioPlayer from "../AudioPlayer";
import PageShadowOverlay from "./PageShadowOverlay";
import type { Dialogue, DialogueAudio } from "../../types/book";
import { getDialogueText, getDialogueAudioUrl } from "../../types/book";

interface PageDialoguesProps {
  dialogues: Dialogue[];
  bookId: string;
  languageCode?: string;
  onAudioError?: () => void;
  refreshedAudios?: DialogueAudio[]; // useMediaUrl에서 갱신된 오디오 URL
}

const PageDialogues = React.memo(
  ({
    dialogues,
    bookId,
    languageCode = "en",
    onAudioError,
    refreshedAudios,
  }: PageDialoguesProps) => {
    // 갱신된 오디오 URL 찾기 (dialogue ID와 language code로 매칭)
    const getRefreshedAudioUrl = (dialogue: Dialogue): string | undefined => {
      if (!refreshedAudios || refreshedAudios.length === 0) {
        // refreshedAudios가 없으면 기존 dialogue의 audio 사용
        return getDialogueAudioUrl(dialogue, languageCode);
      }

      // refreshedAudios에서 해당 dialogue의 audio 찾기
      // dialogue.audios의 첫 번째 audio와 같은 voice_id를 가진 것을 찾음
      const originalAudio = dialogue.audios.find(
        (a) => a.language_code === languageCode
      );

      if (!originalAudio) {
        return getDialogueAudioUrl(dialogue, languageCode);
      }

      // refreshedAudios에서 같은 language_code를 가진 audio 찾기
      const refreshedAudio = refreshedAudios.find(
        (a) => a.language_code === languageCode && a.voice_id === originalAudio.voice_id
      );

      return refreshedAudio?.audio_url || getDialogueAudioUrl(dialogue, languageCode);
    };

    return (
      <div className="relative w-full h-full bg-white flex flex-col justify-center items-center p-10">
        <PageShadowOverlay position="left" opacity="normal" />
        <PageShadowOverlay position="right" opacity="light" />

        <div className="w-full h-full flex flex-col justify-center items-start">
          {dialogues.map((dialogue: Dialogue) => (
            <div
              key={dialogue.id}
              className="relative w-full mb-5 flex items-center justify-start"
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
              onMouseDown={(e: React.MouseEvent) => e.stopPropagation()}
              onTouchStart={(e: React.TouchEvent) => e.stopPropagation()}
            >
              <ClickableText
                text={getDialogueText(dialogue, languageCode)}
                book_id={bookId}
              />
              <AudioPlayer
                src={getRefreshedAudioUrl(dialogue) || ""}
                onError={onAudioError}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }
);

PageDialogues.displayName = "PageDialogues";

export default PageDialogues;
