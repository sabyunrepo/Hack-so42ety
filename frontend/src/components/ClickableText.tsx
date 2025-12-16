import { useState } from "react";
import { getWordTTS } from "../api/index";

interface ClickableTextProps {
  text: string;
  book_id: string;
}
interface CachedAudio {
  filePath: string;
  timestamp: number; // 캐시된 시각 (밀리초)
}
interface AudioCache {
  [key: string]: CachedAudio;
}
const URL_EXPIRY_MS = 58 * 1000;

const ClickableText = ({ text, book_id }: ClickableTextProps) => {
  const [playingWord, setPlayingWord] = useState<string | null>(null);
  const [audioCache, setAudioCache] = useState<AudioCache>({});

  const playWord = async (word: string) => {
    try {
      // 특수문자 제거
      const cleanWord = word.replace(/[^a-zA-Z]/g, "").toLowerCase(); // 소문자로 통일하여 캐시 키 사용

      if (!cleanWord) return;

      setPlayingWord(cleanWord);

      let filePath: string;
      const now = Date.now(); // 현재 시각

      // 2. 캐시 유효성 검사 로직 추가
      const cachedItem = audioCache[cleanWord];
      const isCacheValid =
        cachedItem && now - cachedItem.timestamp < URL_EXPIRY_MS;

      if (isCacheValid) {
        // 2-1. 캐시 유효: 캐시된 URL 사용
        console.log(`캐시(유효)에서 가져옴: ${cleanWord}`);
        filePath = cachedItem.filePath;
      } else {
        // 2-2. 캐시 만료 또는 없음: API 호출하여 새로운 URL 요청
        if (cachedItem) {
          console.log(`캐시 만료됨, API 재호출: ${cleanWord}`);
        } else {
          console.log(`API 호출: ${cleanWord}`);
        }

        // TTS API 호출
        const response = await getWordTTS(cleanWord, book_id);
        filePath = response.audio_url;

        // 캐시 갱신 (새로운 URL과 현재 시각 저장)
        setAudioCache((prev) => ({
          ...prev,
          [cleanWord]: {
            filePath: filePath,
            timestamp: now,
          },
        }));
      }

      // 오디오 재생
      const audio = new Audio(`${filePath}`);
      audio.play();

      audio.onended = () => {
        setPlayingWord(null);
      };
    } catch (error) {
      setPlayingWord(null);
      console.error("오디오 재생 또는 API 호출 중 오류 발생:", error);
    }
  };

  // 텍스트를 단어로 분리
  const words = text.split(/(\s+)/); // 공백 유지

  return (
    <p className="text-base sm:text-lg md:text-lg lg:text-2xl  mb-5  leading-relaxed">
      {words.map((word, index) => {
        const cleanWord = word
          .trim()
          .replace(/[^a-zA-Z]/g, "")
          .toLowerCase();

        // 공백이나 빈 문자열은 그대로 표시
        if (!cleanWord) {
          return <span key={index}>{word}</span>;
        }

        const isPlaying = playingWord === cleanWord;

        return (
          <span
            key={index}
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              playWord(word);
            }}
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            className={`cursor-pointer hover:bg-yellow-200 hover:text-yellow-800 rounded px-1 transition-all ${
              isPlaying ? "bg-yellow-300 text-yellow-900" : ""
            }`}
            title={`Click to hear: ${cleanWord}`}
          >
            {word}
          </span>
        );
      })}
    </p>
  );
};

export default ClickableText;
