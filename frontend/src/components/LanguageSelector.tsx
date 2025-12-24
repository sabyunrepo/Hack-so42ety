import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '../i18n/config';

export default function LanguageSelector() {
  const { i18n } = useTranslation();

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLang = e.target.value as SupportedLanguage;
    i18n.changeLanguage(newLang);
    // localStorage에 자동 저장됨 (LanguageDetector 설정에 의해)
  };

  // 현재 언어 코드 정규화 (예: ko-KR -> ko)
  const currentLanguage = i18n.language.split('-')[0] as SupportedLanguage;

  return (
    <div className="flex items-center gap-1 sm:gap-2">
      <Globe className="w-4 h-4 sm:w-5 sm:h-5 text-[#3D3D3D]" />
      <select
        value={currentLanguage}
        onChange={handleLanguageChange}
        className="bg-transparent border border-[#3D3D3D]/30 rounded-md px-1 py-0.5 sm:px-2 sm:py-1 text-xs sm:text-sm text-[#3D3D3D] focus:outline-none focus:ring-2 focus:ring-[#3D3D3D]/50 cursor-pointer"
        aria-label="Select language"
      >
        {Object.entries(SUPPORTED_LANGUAGES).map(([code, name]) => (
          <option key={code} value={code}>
            {name}
          </option>
        ))}
      </select>
    </div>
  );
}
