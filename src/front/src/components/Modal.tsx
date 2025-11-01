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

export default function Modal({
  isOpen,
  onClose,
  title = "요청 완료!",
  message = "요청이 성공적으로 처리되었습니다.",
  submessage,
  buttonText = "확인",
  redirectTo,
  onConfirm
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
          <p className="text-gray-600 mb-2">
            {message}
          </p>
          {submessage && (
            <p className="text-sm text-gray-500 mt-2">
              {submessage}
            </p>
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