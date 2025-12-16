import { useState } from "react";
import { getWordTTS } from "../api/index";

interface ClickableTextProps {
  text: string;
  book_id: string;
}

const ClickableText = ({ text, book_id }: ClickableTextProps) => {
  const [playingWord, setPlayingWord] = useState<string | null>(null);

  const playWord = async (word: string) => {
    try {
      // 특수문자 제거
      const cleanWord = word.replace(/[^a-zA-Z]/g, "").toLowerCase(); // 소문자로 통일하여 캐시 키 사용

      if (!cleanWord) return;

      setPlayingWord(cleanWord);
        // TTS API 호출
        const response = await getWordTTS(cleanWord, book_id);
        const filePath = response.audio_url;


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
