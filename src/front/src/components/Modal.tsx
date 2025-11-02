import { useNavigate } from "react-router-dom";

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
