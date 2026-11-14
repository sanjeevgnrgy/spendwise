// A hook for components that depend on the language itself rather than on a text: the language menu, and anything
// that needs the date picker's locale. Part of shared/i18n.

import type { DayPickerLocale } from "react-day-picker"
import { useTranslation } from "react-i18next"

import { currentDatePickerLocale, currentLanguage, setLanguage } from "./i18n"
import { LANGUAGES, type Language } from "./languages"

/** The language on now, what it needs for formatting, and how to switch. */
export interface LanguageState {
  /** The language's code ("en", "hi"). */
  language: Language
  /** Its name in itself ("हिन्दी"). */
  name: string
  /** The Intl locale numbers and dates are written in ("hi-IN"). */
  locale: string
  /** Which way its text runs. */
  dir: "ltr" | "rtl"
  /** The date picker's locale (month and weekday names, screen-reader labels). */
  datePickerLocale: DayPickerLocale | undefined
  /** Switch language (and save the choice); rejects if its texts couldn't be loaded. */
  setLanguage: (next: Language) => Promise<void>
}

/** The current language. The component re-renders when it changes (react-i18next's languageChanged binding). */
export function useLanguage(): LanguageState {
  // Subscribes this component to language changes; the language itself is read from the shared instance.
  useTranslation()
  const language = currentLanguage()
  const { name, locale, dir } = LANGUAGES[language]
  return { language, name, locale, dir, datePickerLocale: currentDatePickerLocale(), setLanguage }
}
