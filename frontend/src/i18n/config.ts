import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import Korean translations
import koCommon from './locales/ko/common.json';
import koAuth from './locales/ko/auth.json';
import koBookshelf from './locales/ko/bookshelf.json';
import koCreator from './locales/ko/creator.json';
import koSettings from './locales/ko/settings.json';
import koViewer from './locales/ko/viewer.json';
import koModal from './locales/ko/modal.json';
import koError from './locales/ko/error.json';

// Import English translations
import enCommon from './locales/en/common.json';
import enAuth from './locales/en/auth.json';
import enBookshelf from './locales/en/bookshelf.json';
import enCreator from './locales/en/creator.json';
import enSettings from './locales/en/settings.json';
import enViewer from './locales/en/viewer.json';
import enModal from './locales/en/modal.json';
import enError from './locales/en/error.json';

// Import Chinese translations
import zhCommon from './locales/zh/common.json';
import zhAuth from './locales/zh/auth.json';
import zhBookshelf from './locales/zh/bookshelf.json';
import zhCreator from './locales/zh/creator.json';
import zhSettings from './locales/zh/settings.json';
import zhViewer from './locales/zh/viewer.json';
import zhModal from './locales/zh/modal.json';
import zhError from './locales/zh/error.json';

// Import Vietnamese translations
import viCommon from './locales/vi/common.json';
import viAuth from './locales/vi/auth.json';
import viBookshelf from './locales/vi/bookshelf.json';
import viCreator from './locales/vi/creator.json';
import viSettings from './locales/vi/settings.json';
import viViewer from './locales/vi/viewer.json';
import viModal from './locales/vi/modal.json';
import viError from './locales/vi/error.json';

// Import Russian translations
import ruCommon from './locales/ru/common.json';
import ruAuth from './locales/ru/auth.json';
import ruBookshelf from './locales/ru/bookshelf.json';
import ruCreator from './locales/ru/creator.json';
import ruSettings from './locales/ru/settings.json';
import ruViewer from './locales/ru/viewer.json';
import ruModal from './locales/ru/modal.json';
import ruError from './locales/ru/error.json';

// Import Thai translations
import thCommon from './locales/th/common.json';
import thAuth from './locales/th/auth.json';
import thBookshelf from './locales/th/bookshelf.json';
import thCreator from './locales/th/creator.json';
import thSettings from './locales/th/settings.json';
import thViewer from './locales/th/viewer.json';
import thModal from './locales/th/modal.json';
import thError from './locales/th/error.json';

// Supported languages
export const SUPPORTED_LANGUAGES = {
  ko: '한국어',
  en: 'English',
  zh: '中文',
  vi: 'Tiếng Việt',
  ru: 'Русский',
  th: 'ไทย',
} as const;

export type SupportedLanguage = keyof typeof SUPPORTED_LANGUAGES;

// Translation resources
const resources = {
  ko: {
    common: koCommon,
    auth: koAuth,
    bookshelf: koBookshelf,
    creator: koCreator,
    settings: koSettings,
    viewer: koViewer,
    modal: koModal,
    error: koError,
  },
  en: {
    common: enCommon,
    auth: enAuth,
    bookshelf: enBookshelf,
    creator: enCreator,
    settings: enSettings,
    viewer: enViewer,
    modal: enModal,
    error: enError,
  },
  zh: {
    common: zhCommon,
    auth: zhAuth,
    bookshelf: zhBookshelf,
    creator: zhCreator,
    settings: zhSettings,
    viewer: zhViewer,
    modal: zhModal,
    error: zhError,
  },
  vi: {
    common: viCommon,
    auth: viAuth,
    bookshelf: viBookshelf,
    creator: viCreator,
    settings: viSettings,
    viewer: viViewer,
    modal: viModal,
    error: viError,
  },
  ru: {
    common: ruCommon,
    auth: ruAuth,
    bookshelf: ruBookshelf,
    creator: ruCreator,
    settings: ruSettings,
    viewer: ruViewer,
    modal: ruModal,
    error: ruError,
  },
  th: {
    common: thCommon,
    auth: thAuth,
    bookshelf: thBookshelf,
    creator: thCreator,
    settings: thSettings,
    viewer: thViewer,
    modal: thModal,
    error: thError,
  },
};

i18n
  .use(LanguageDetector) // Browser language detection
  .use(initReactI18next) // React integration
  .init({
    resources,
    fallbackLng: 'ko', // Default language: Korean
    defaultNS: 'common', // Default namespace
    ns: ['common', 'auth', 'bookshelf', 'creator', 'settings', 'viewer', 'modal', 'error'],

    // Browser language detection settings
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },

    interpolation: {
      escapeValue: false, // React already handles XSS protection
    },

    // Supported languages
    supportedLngs: ['ko', 'en', 'zh', 'vi', 'ru', 'th'],

    // Development mode debugging
    debug: import.meta.env.DEV,
  });

export default i18n;
