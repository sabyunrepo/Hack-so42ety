import React, { useMemo } from "react";
import ClickableText from "../ClickableText";
import AudioPlayer from "../AudioPlayer";
import PageShadowOverlay from "./PageShadowOverlay";
import type { Dialogue, DialogueAudio } from "../../types/book";
import { getDialogueText, getDialogueAudioUrl } from "../../types/book";
import { useMediaUrl } from "../../hooks/useMediaUrl";

interface PageDialoguesProps {
  dialogues: Dialogue[];
  bookId: string;
  pageId: string; //  추가 필요
  languageCode?: string;
  isShared: boolean;
}

const PageDialogues = React.memo(
  ({
    dialogues,
    bookId,
    pageId,
    languageCode = "en",
    isShared,
  }: PageDialoguesProps) => {
    // 초기 오디오 URL 목록 생성
    const initialAudios = useMemo(() => {
      const audios: DialogueAudio[] = [];
      dialogues.forEach((dialogue) => {
        dialogue.audios.forEach((audio) => {
          audios.push({
            language_code: audio.language_code,
            voice_id: audio.voice_id,
            audio_url: audio.audio_url,
          });
        });
      });
      return audios;
    }, [dialogues]);

    // useMediaUrl 훅 사용
    const { urls, refreshUrls } = useMediaUrl({
      bookId,
      pageId,
      initialUrls: { audios: initialAudios },
      isShared,
    });

    // 갱신된 오디오 URL 찾기
    const getRefreshedAudioUrl = (dialogue: Dialogue): string | undefined => {
      if (!urls.audios || urls.audios.length === 0) {
        // urls.audios가 없으면 기존 dialogue의 audio 사용
        return getDialogueAudioUrl(dialogue, languageCode);
      }

      // dialogue에서 해당 언어의 original audio 찾기
      const originalAudio = dialogue.audios.find(
        (a) => a.language_code === languageCode
      );

      if (!originalAudio) {
        return getDialogueAudioUrl(dialogue, languageCode);
      }

      // urls.audios에서 같은 language_code와 voice_id를 가진 audio 찾기
      const refreshedAudio = urls.audios.find(
        (a) =>
          a.language_code === languageCode &&
          a.voice_id === originalAudio.voice_id
      );

      return (
        refreshedAudio?.audio_url || getDialogueAudioUrl(dialogue, languageCode)
      );
    };

    // 오디오 에러 처리 개선
    const handleAudioError = async () => {
      if (!isShared) {
        console.warn("Audio failed to load, attempting refresh...");
        try {
          await refreshUrls();
        } catch (err) {
          console.error("Failed to refresh audio URLs:", err);
        }
      }
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
                onError={handleAudioError}
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
