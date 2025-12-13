import { useState } from "react";
import { getWordTTS } from "../api/index";

interface ClickableTextProps {
  text: string;
  book_id: string;
}

interface AudioCache {
  [key: string]: string;
}

const ClickableText = ({ text, book_id }: ClickableTextProps) => {
  const [playingWord, setPlayingWord] = useState<string | null>(null);
  const [audioCache, setAudioCache] = useState<AudioCache>({});

  const playWord = async (word: string) => {
    try {
      // 특수문자 제거
      const cleanWord = word.replace(/[^a-zA-Z]/g, "").toLowerCase();

      if (!cleanWord) return;

      setPlayingWord(cleanWord);

      let filePath: string;

      // 캐시에 있는지 확인
      if (audioCache[cleanWord]) {
        console.log(`캐시에서 가져옴: ${cleanWord}`);
        filePath = audioCache[cleanWord];
      } else {
        console.log(`API 호출: ${cleanWord}`);
        // TTS API 호출
        const response = await getWordTTS(cleanWord, book_id);
        filePath = response.audio_url; // file_path 대신 audio_url 사용
        // 캐시에 저장
        setAudioCache((prev) => ({
          ...prev,
          [cleanWord]: filePath,
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
      console.error(error);
    }
  };

  // 텍스트를 단어로 분리
  const words = text.split(/(\s+)/); // 공백 유지

  return (
    <p className="text-2xl p-6 leading-relaxed">
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
              isPlaying ? "bg-yellow-300 text-yellow-900 font-bold" : ""
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
