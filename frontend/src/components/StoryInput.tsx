import { useState, useRef } from "react";
import Img_Icon from "../assets/img.svg";
import { AlertModal } from "./Modal";

interface Page {
  id: number;
  image: File | null;
  story: string;
}

interface StoryInputProps {
  page: Page;
  updatePage: <K extends keyof Page>(id: number, field: K, value: Page[K]) => void;
}

export default function StoryInput({
  page,
  updatePage,
}: StoryInputProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState("");

  const convertHeicToJpeg = async (file: File): Promise<File> => {
    try {
      const heic2any = (await import('heic2any')).default;
      const convertedBlob = await heic2any({
        blob: file,
        toType: 'image/jpeg',
        quality: 0.8,
      });

      // heic2any는 Blob 또는 Blob[]를 반환할 수 있음
      const blob = Array.isArray(convertedBlob) ? convertedBlob[0] : convertedBlob;

      // Blob을 File 객체로 변환
      return new File([blob], file.name.replace(/\.(heic|heif)$/i, '.jpg'), {
        type: 'image/jpeg',
      });
    } catch {
      throw new Error('HEIC 파일 변환에 실패했습니다.');
    }
  };

  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // 파일 타입 검증 (png, jpg, jpeg, heic, heif 허용)
      const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/heic', 'image/heif'];
      if (!allowedTypes.includes(file.type)) {
        setAlertMessage('PNG, JPG, JPEG, HEIC 파일만 업로드 가능합니다.');
        setShowAlert(true);
        e.target.value = ''; // 입력 초기화
        return;
      }

      // 파일 크기 검증 (5MB 이하)
      const maxSize = 15 * 1024 * 1024; // 5MB in bytes
      if (file.size > maxSize) {
        setAlertMessage('파일 크기는 15MB 이하만 가능합니다.');
        setShowAlert(true);
        e.target.value = ''; // 입력 초기화
        return;
      }

      let processedFile = file;

      // HEIC/HEIF 파일인 경우 JPEG로 변환
      if (file.type === 'image/heic' || file.type === 'image/heif') {
        try {
          processedFile = await convertHeicToJpeg(file);
        } catch (error) {
          setAlertMessage(error instanceof Error ? error.message : 'HEIC 파일 변환에 실패했습니다.');
          setShowAlert(true);
          e.target.value = ''; // 입력 초기화
          return;
        }
      }

      updatePage(page.id, "image", processedFile);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(processedFile);
    }
  };

  const handleStoryChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    updatePage(page.id, "story", e.target.value);
  };

  const handleImageClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <>
      <div className="bg-white rounded-3xl shadow-lg p-4 sm:p-5 md:p-6 flex gap-4 sm:gap-5 md:gap-6 items-start relative transition-all w-full">
        {/* 이미지 업로드 영역 */}
        <div
          onClick={handleImageClick}
          className="w-20 h-20 sm:w-24 sm:h-24 md:w-28 md:h-28 lg:w-32 lg:h-32 rounded-lg bg-gray-100 flex-shrink-0 flex items-center justify-center cursor-pointer overflow-hidden hover:bg-gray-200 transition-colors"
        >
          <input
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/heic,image/heif"
            ref={fileInputRef}
            onChange={handleImageChange}
            className="hidden"
          />
          {preview ? (
            <img
              src={preview}
              alt="Preview"
              className="w-full h-full object-cover"
            />
          ) : (
            <img className="w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12" src={Img_Icon} alt="Upload" />
          )}
        </div>

        {/* 텍스트 입력 영역 */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="relative">
            <textarea
              value={page.story}
              onChange={handleStoryChange}
              placeholder="여기에 이야기를 입력하세요..."
              className="w-full h-20 sm:h-24 md:h-28 lg:h-32 border border-gray-200 rounded-lg p-2 sm:p-2.5 md:p-3 pr-12 sm:pr-14 md:pr-16 resize-none focus:outline-none focus:ring-2 focus:ring-amber-400 text-sm sm:text-base"
              maxLength={100}
            />
            <div className="absolute bottom-1.5 sm:bottom-2 right-1.5 sm:right-2 text-gray-600 text-xs sm:text-sm bg-white px-1 rounded">
              {page.story.length}/100
            </div>
          </div>
        </div>
      </div>

      {/* Alert Modal */}
      <AlertModal
        isOpen={showAlert}
        onClose={() => setShowAlert(false)}
        title="업로드 오류"
        message={alertMessage}
        buttonText="확인"
      />
    </>
  );
}
