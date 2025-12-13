import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Copy, Check } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  message?: string;
  submessage?: string;
  buttonText?: string;
  redirectTo?: string; // 리다이렉트할 경로
  onConfirm?: () => void; // 확인 버튼 클릭 시 추가 동작
}

interface ScriptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ConfirmModal({
  isOpen,
  onClose,
  title,
  onConfirm,
}: ModalProps) {
  const handleConfirm = () => {
    // 추가 동작이 있으면 실행
    if (onConfirm) {
      onConfirm();
    }

    // 모달 닫기
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600/30 bg-opacity-50 flex items-center justify-center z-50">
      <div className="w-96 h-80 relative bg-white rounded-[33px] shadow-xl">
        {/* X 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center text-gray-600 hover:text-gray-800 text-2xl font-bold"
        >
          ×
        </button>

        {/* 경고 아이콘 (노란색 원형) */}
        <div className="absolute top-14 left-1/2 transform -translate-x-1/2">
          <div className="w-14 h-14 bg-amber-400 rounded-full flex items-center justify-center">
            <span className="text-white text-2xl font-bold">!</span>
          </div>
        </div>

        {/* 제목 텍스트 */}
        <div className="absolute top-36 left-1/2 transform -translate-x-1/2 text-center">
          <h3 className="text-black text-2xl font-bold font-['Roboto'] leading-7">
            {title || "삭제 하시겠습니까?"}
          </h3>
        </div>

        {/* 버튼들 */}
        <div className="absolute bottom-16 left-1/2 transform -translate-x-1/2 flex gap-4">
          {/* 네 버튼 (취소) */}
          <button
            onClick={handleConfirm}
            className="w-28 h-12 bg-white rounded-xl border-[3px] border-amber-400 flex items-center justify-center hover:bg-gray-50 transition-colors"
          >
            <span className="text-black text-xl font-normal font-['Roboto']">
              네
            </span>
          </button>

          {/* 아니오 버튼 (확인) */}
          <button
            onClick={onClose}
            className="w-28 h-12 bg-amber-400 rounded-xl border-[3px] border-amber-400 flex items-center justify-center hover:bg-amber-500 transition-colors"
          >
            <span className="text-black text-xl font-normal font-['Roboto']">
              아니오
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

export function AlertModal({
  isOpen,
  onClose,
  title = "요청 완료!",
  message = "요청이 성공적으로 처리되었습니다.",
  submessage,
  buttonText = "확인",
  redirectTo,
  onConfirm,
}: ModalProps) {
  const navigate = useNavigate();

  const handleConfirm = () => {
    // 추가 동작이 있으면 실행
    if (onConfirm) {
      onConfirm();
    }

    // 모달 닫기
    onClose();

    // 리다이렉트가 설정되어 있으면 페이지 이동
    if (redirectTo) {
      navigate(redirectTo);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600/30 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-8 max-w-md mx-4 shadow-2xl">
        {/* 제목 */}
        <h3 className="text-xl font-bold text-gray-900 mb-4 text-center">
          {title}
        </h3>

        {/* 메시지 */}
        <div className="text-center mb-6">
          <p className="text-gray-600 mb-2">{message}</p>
          {submessage && (
            <p className="text-sm text-gray-500 mt-2">{submessage}</p>
          )}
        </div>

        {/* 확인 버튼 */}
        <button
          onClick={handleConfirm}
          className="w-full py-3 bg-yellow-400 text-white font-semibold rounded-lg hover:bg-yellow-500 transition-colors"
        >
          {buttonText}
        </button>
      </div>
    </div>
  );
}

// 녹음용 대본 섹션별 데이터
interface ScriptSection {
  emoji: string;
  title: string;
  lines: { emotion: string; english: string; korean: string }[];
}

const RECORDING_SECTIONS: ScriptSection[] = [
  {
    emoji: "🌅",
    title: "아침 인사와 일상",
    lines: [
      { emotion: "쾌활함, 활기", english: "Good morning, world!", korean: "굿 모닝, 월드!" },
      { emotion: "기쁨, 놀라움", english: "The sun is actually out.", korean: "더 썬 이즈 액츄얼리 아웃." },
      { emotion: "친근함, 긍정적", english: "That's a solid start to any day, isn't it?", korean: "댓츠 어 솔리드 스타트 투 애니 데이, 이즌트 잇?" },
      { emotion: "가벼운 농담", english: "I swear, this apartment only gets sunlight for about five minutes a year.", korean: "아이 스웨어, 디스 아파트먼트 온리 겟츠 썬라이트 포 어바웃 파이브 미니츠 어 이어." },
      { emotion: "차분함, 즐거움", english: "I'm going to take a moment to really soak it in.", korean: "아임 고잉 투 테이크 어 모먼트 투 리얼리 소크 잇 인." }
    ]
  },
  {
    emoji: "🗺️",
    title: "오늘의 모험 계획",
    lines: [
      { emotion: "호기심, 설렘", english: "Okay, what adventure should I choose today?", korean: "오케이, 왓 어드벤처 슈드 아이 추즈 투데이?" },
      { emotion: "질문, 고민", english: "Should I finally try that tiny new bakery on Elm Street?", korean: "슈드 아이 파이널리 트라이 댓 타이니 뉴 베이커리 온 엘름 스트리트?" },
      { emotion: "강조, 행복함", english: "The one that smells like cinnamon and absolute happiness?", korean: "더 원 댓 스멜즈 라이크 시나몬 앤 앱솔루트 해피니스?" },
      { emotion: "장난스러움", english: "Or maybe I should finally finish building that impossible LEGO castle.", korean: "오어 메이비 아이 슈드 파이널리 피니시 빌딩 댓 임파서블 레고 캐슬." },
      { emotion: "좌절(가벼운), 투지", english: "I'm about three pieces short of total victory, but those last pieces are hiding somewhere!", korean: "아임 어바웃 쓰리 피시즈 쇼트 오브 토탈 빅토리, 벗 도즈 라스트 피시즈 아 하이딩 썸웨어!" }
    ]
  },
  {
    emoji: "💌",
    title: "따뜻한 추억",
    lines: [
      { emotion: "부드러움, 회상", english: "It reminds me of when I was a kid.", korean: "잇 리마인즈 미 오브 웬 아이 워즈 어 키드." },
      { emotion: "애정, 평화로움", english: "My grandmother used to tell me that every morning was a chance to draw a brand new map.", korean: "마이 그랜드마더 유즈드 투 텔 미 댓 에브리 모닝 워즈 어 찬스 투 드로우 어 브랜드 뉴 맵." },
      { emotion: "인용구(따뜻함)", english: "She said, \"You get to choose where the treasure goes.\"", korean: "쉬 세드, \"유 겟 투 추즈 웨어 더 트레저 고즈.\"" },
      { emotion: "순수함, 웃음", english: "I genuinely believed that if I drew the map well enough, I'd find real pirate gold.", korean: "아이 제뉴인리 빌리브드 댓 이프 아이 드류 더 맵 웰 이너프, 아일 파인드 리얼 파이럿 골드." },
      { emotion: "만족스러움", english: "I didn't find the gold, but I always found an adventure.", korean: "아이 디든트 파인드 더 골드, 벗 아이 올웨이즈 파운드 언 어드벤처." }
    ]
  },
  {
    emoji: "💪",
    title: "열정과 확신",
    lines: [
      { emotion: "수사적 질문", english: "That's what life is, isn't it?", korean: "댓츠 왓 라이프 이즈, 이즌트 잇?" },
      { emotion: "열정, 단호함", english: "It's not about avoiding the rainy days, it's about choosing to dance in them!", korean: "잇츠 낫 어바웃 어보이딩 더 레이니 데이즈, 잇츠 어바웃 추징 투 댄스 인 뎀!" },
      { emotion: "설득, 고조", english: "You have to look for the tiny bursts of color, the unexpected good news, the kindness that pops up when you least expect it!", korean: "유 해브 투 룩 포 더 타이니 버스츠 오브 컬러, 디 언익스펙티드 굿 뉴스, 더 카인드니스 댓 팝스 업 웬 유 리스트 엑스펙트 잇!" },
      { emotion: "진지함", english: "The world throws a lot of negativity at us.", korean: "더 월드 쓰로우즈 어 뢋 오브 네가티비티 앳 어스." },
      { emotion: "강력한 의지", english: "You have to push back!", korean: "유 해브 투 푸시 백!" },
      { emotion: "최대 강조", english: "You have to decide to be your own sunshine!", korean: "유 해브 투 디사이드 투 비 유어 오운 썬샤인!" }
    ]
  },
  {
    emoji: "🫂",
    title: "위로와 격려",
    lines: [
      { emotion: "조언, 차분함", english: "Remember that.", korean: "리멤버 댓." },
      { emotion: "공감, 위로", english: "If you're feeling a little lost today, that's okay.", korean: "이프 유아 필링 어 리틀 로스트 투데이, 댓츠 오케이." },
      { emotion: "격려", english: "Just take one step.", korean: "저스트 테이크 원 스텝." },
      { emotion: "구체적 제안", english: "Maybe it's putting on your favorite song, or drinking a truly fantastic cup of coffee.", korean: "메이비 잇츠 푸팅 온 유어 페이버릿 송, 오어 드링킹 어 트루리 판타스틱 컵 오브 커피." },
      { emotion: "현명함, 통찰력", english: "Sometimes the biggest victories are the tiny, quiet ones.", korean: "섬타임즈 더 비기스트 빅토리즈 아 더 타이니, 콰이어트 원즈." }
    ]
  },
  {
    emoji: "✨",
    title: "마지막 결의",
    lines: [
      { emotion: "쾌활함", english: "Alright, let's go find that cinnamon-smelling treasure.", korean: "올롸이트, 레츠 고 파인드 댓 시나몬-스멜링 트레저." },
      { emotion: "확신, 기분 좋음", english: "I have a feeling today is going to be genuinely great.", korean: "아이 해브 어 필링 투데이 이즈 고잉 투 비 제뉴인리 그레이트." },
      { emotion: "독려", english: "You just have to open your eyes and look for the magic.", korean: "유 저스트 해브 투 오픈 유어 아이즈 앤 룩 포 더 매직." },
      { emotion: "에너지, 결의", english: "Let's do this!", korean: "레츠 두 디스!" }
    ]
  }
];

export function ScriptModal({ isOpen, onClose }: ScriptModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      // 전체 대본을 플레인 텍스트로 변환
      const fullScript = RECORDING_SECTIONS.map((section) =>
        section.lines
          .map((line) => `${line.english}\n${line.korean}`)
          .join("\n\n")
      ).join("\n\n---\n\n");

      await navigator.clipboard.writeText(fullScript);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("복사 실패:", err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-yellow-50 to-orange-50">
          <div>
            <h3 className="text-2xl font-bold text-gray-900">🎙️ 녹음용 대본</h3>
            <p className="text-sm text-gray-600 mt-1">
              감정을 살려 천천히 읽어주세요
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-3xl font-bold leading-none transition-colors"
          >
            ×
          </button>
        </div>

        {/* 안내 메시지 */}
        <div className="px-6 pt-4 pb-2">
          <div className="bg-blue-50 border-l-4 border-blue-400 rounded-r-lg p-4">
            <p className="text-sm text-gray-700 leading-relaxed">
              💡 <strong>녹음 가이드:</strong> 각 문장의 감정/톤을 참고하여{" "}
              <strong className="text-blue-700">천천히, 또렷하게</strong> 읽어주세요.
              <br />⏱️ 권장 녹음 시간: <strong className="text-blue-700">2분 30초 ~ 3분</strong>
            </p>
          </div>
        </div>

        {/* 대본 내용 - 스크롤 가능 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="space-y-6">
            {RECORDING_SECTIONS.map((section, sectionIdx) => (
              <div
                key={sectionIdx}
                className="bg-gradient-to-br from-gray-50 to-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow"
              >
                {/* 섹션 제목 */}
                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200">
                  {/* <span className="text-3xl">{section.emoji}</span> */}
                  <h4 className="text-lg font-bold text-gray-800">
                    {sectionIdx + 1}. {section.title}
                  </h4>
                </div>

                {/* 섹션 내용 */}
                <div className="space-y-4">
                  {section.lines.map((line, lineIdx) => (
                    <div
                      key={lineIdx}
                      className="bg-white rounded-lg p-4 border border-gray-100"
                    >
                      {/* 감정/톤 태그 */}
                      <div className="mb-2">
                        <span className="inline-block px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full">
                          {line.emotion}
                        </span>
                      </div>

                      {/* 영어 원문 */}
                      <p className="text-base font-medium text-gray-900 mb-2 leading-relaxed">
                        {line.english}
                      </p>

                      {/* 한글 발음 */}
                      <p className="text-sm text-gray-600 leading-relaxed">
                        🔊 {line.korean}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 하단 버튼 */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 flex gap-3">
          <button
            onClick={handleCopy}
            className={`flex-1 py-3 rounded-lg font-semibold transition-all flex items-center justify-center gap-2 shadow-sm ${
              copied
                ? "bg-green-500 text-white"
                : "bg-yellow-400 text-white hover:bg-yellow-500 hover:shadow-md"
            }`}
          >
            {copied ? (
              <>
                <Check className="w-5 h-5" />
                복사 완료!
              </>
            ) : (
              <>
                <Copy className="w-5 h-5" />
                전체 대본 복사
              </>
            )}
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100 transition-all shadow-sm"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
