import 'react-i18next';
import type common from './locales/ko/common.json';
import type auth from './locales/ko/auth.json';
import type bookshelf from './locales/ko/bookshelf.json';
import type creator from './locales/ko/creator.json';
import type settings from './locales/ko/settings.json';
import type viewer from './locales/ko/viewer.json';
import type modal from './locales/ko/modal.json';
import type error from './locales/ko/error.json';

declare module 'react-i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common';
    resources: {
      common: typeof common;
      auth: typeof auth;
      bookshelf: typeof bookshelf;
      creator: typeof creator;
      settings: typeof settings;
      viewer: typeof viewer;
      modal: typeof modal;
      error: typeof error;
    };
  }
}
