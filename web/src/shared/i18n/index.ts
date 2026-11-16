// Translation's public face: which languages the app speaks, loading and switching their texts, and the language menu.
// Part of shared/ (it knows no feature: each feature defines its own namespaces with defineNamespace, loads them from
// its page's lazy loader with loadNamespaces, and app/_shell/namespaces.ts lists the frame's, which
// app/_shell/client-root.tsx hands to initI18n). Components read texts with their namespace's useTexts hook.

export type { CommonTexts } from "./common"
export {
  ACCEPT_LANGUAGE,
  currentDatePickerLocale,
  currentLanguage,
  currentLanguageInfo,
  i18n,
  initI18n,
  languageHeaders,
  loadNamespaces,
  setLanguage,
} from "./i18n"
export { LanguageMenu } from "./language-menu"
export { DEFAULT_LANGUAGE, isLanguage, LANGUAGE_CODES, LANGUAGES, type Language, type LanguageInfo } from "./languages"
export { defineNamespace, type AnyNamespace, type Namespace, type Texts, type Translation } from "./namespace"
export { useLanguage, type LanguageState } from "./use-language"
