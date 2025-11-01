import { useState, useRef } from "react";
// import MyImage from "../assets/img.svg";

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

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      updatePage(page.id, "image", file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleStoryChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    updatePage(page.id, "story", e.target.value);
  };

  const handleImageClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="bg-white flex-1 rounded-3xl shadow-lg p-6 flex gap-6 items-start relative transition-all w-[680px]">
      {/* 이미지 업로드 영역 */}
      <div
        onClick={handleImageClick}
        className="w-32 h-32 rounded-lg bg-gray-100 flex-shrink-0 flex items-center justify-center cursor-pointer overflow-hidden hover:bg-gray-200 transition-colors"
      >
        <input
          type="file"
          accept="image/*"
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
          // <img className="w-12 h-12" src={MyImage} alt="Upload" />
          <div>test</div>
        )}
      </div>

      {/* 텍스트 입력 영역 */}
      <div className="flex-1 flex flex-col">
        <textarea
          value={page.story}
          onChange={handleStoryChange}
          placeholder="여기에 이야기를 입력하세요..."
          className="w-full h-32 border border-gray-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </div>
    </div>
  );
}
