// The app's one i18next instance, and how texts reach it. Part of shared/i18n. app/_shell/client-root.tsx awaits
// initI18n (shared/'s and the app frame's texts) before drawing anything; each page's and panel's lazy loader awaits
// loadNamespaces for its own texts together with its code; the language menu calls setLanguage. Components read texts
// with their namespace's useTexts hook (react-i18next); code outside components uses i18n.t and currentLanguage.
//
// i18next is given no backend: the app imports each file itself and adds it with addResourceBundle once every file
// it needs has arrived. A failed attempt (offline) so adds nothing and leaves nothing marked as failed, and trying
// again really fetches again. (i18next's own loader remembers a failure and never retries it.)

import i18next from "i18next"
import type { DayPickerLocale } from "react-day-picker"
import { initReactI18next } from "react-i18next"

import { commonTexts } from "./common"
import {
  DEFAULT_LANGUAGE,
  LANGUAGE_CODES,
  LANGUAGE_STORAGE_KEY,
  LANGUAGES,
  initialLanguage,
  isLanguage,
  type Language,
  type LanguageInfo,
} from "./languages"
import type { AnyNamespace } from "./namespace"

// Without a namespace, t() reads "common" (shared/'s texts). Features always name their own.
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: typeof commonTexts.name
  }
}

/** The app's i18next instance. Components use their namespace's useTexts(); other code may call i18n.t(...). */
export const i18n = i18next

/** The request header that asks the server for a language (RFC 9110): it writes its texts (cards, errors) in it. */
export const ACCEPT_LANGUAGE = "Accept-Language"

// The namespaces in use: shared/'s and the app frame's from the start, then each page's or panel's the first time
// it's opened. A language switch loads the new language for these; a page opened later loads its own then.
const inUse = new Set<AnyNamespace>()
// Each language's date picker locale, loaded with its texts before the language is switched on.
const datePickerLocales = new Map<Language, DayPickerLocale>()
// Settles once initI18n has finished: a page's loader may run earlier (the chat panel preloads as its module is
// imported), and i18next can't take texts before it's started.
let markStarted: () => void = () => {}
const started = new Promise<void>((resolve) => {
  markStarted = resolve
})
// The language a switch is loading, while it does: a page opened meanwhile loads it too, so it isn't left behind.
let switchingTo: Language | undefined
// Counts switches, so only the latest choice is switched on when several overlap (the slowest mustn't win).
let latestSwitch = 0

// The languages to load for `language`: itself, and English, the fallback for any text a translation lacks.
function withFallback(language: Language): Language[] {
  return language === DEFAULT_LANGUAGE ? [language] : [language, DEFAULT_LANGUAGE]
}

// Load `namespaces` in `language` (and its fallback) into i18next, skipping files already there. Every file is
// fetched before any is added, so the store never holds half a language. Rejects if any file can't be loaded.
async function loadTexts(namespaces: Iterable<AnyNamespace>, language: Language): Promise<void> {
  const wanted = [...namespaces].flatMap((namespace) =>
    withFallback(language)
      .filter((lng) => !i18n.hasResourceBundle(lng, namespace.name))
      .map((lng) => ({ namespace, lng })),
  )
  const files = await Promise.all(
    wanted.map(async ({ namespace, lng }) => ({ namespace, lng, texts: (await namespace.load[lng]()).default })),
  )
  for (const { namespace, lng, texts } of files) i18n.addResourceBundle(lng, namespace.name, texts)
}

// Load `language` for every namespace in use, again until none came into use meanwhile (a page opened mid-load).
async function loadInUse(language: Language): Promise<void> {
  let count: number
  do {
    count = inUse.size
    await loadTexts(inUse, language)
  } while (inUse.size !== count)
}

// Load everything `language` needs before it's switched on: the texts in use, and its date picker locale. The locale
// is optional: if it can't be loaded, the picker uses English names, and the next switch tries again.
async function prepare(language: Language): Promise<void> {
  const [, datePickerLocale] = await Promise.all([
    loadInUse(language),
    datePickerLocales.get(language) ?? LANGUAGES[language].loadDatePickerLocale().catch(() => undefined),
  ])
  if (datePickerLocale) datePickerLocales.set(language, datePickerLocale)
}

/**
 * Start i18next with the namespaces needed from the first paint (shared/'s "common" is always included), in the
 * starting language (initialLanguage: the saved choice, else the browser's). Resolves once their texts are loaded,
 * so the first paint is already in that language. If that language can't be loaded, the app starts in English.
 * Keeps <html lang> and <html dir> in step with the language.
 */
export async function initI18n(namespaces: readonly AnyNamespace[]): Promise<void> {
  for (const namespace of [commonTexts, ...namespaces]) inUse.add(namespace)
  i18n.on("languageChanged", (language) => {
    // Screen readers, hyphenation and fonts follow the page's language; the layout follows its direction.
    document.documentElement.lang = language
    if (isLanguage(language)) document.documentElement.dir = LANGUAGES[language].dir
  })
  await i18n.use(initReactI18next).init({
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: LANGUAGE_CODES,
    ns: [commonTexts.name],
    defaultNS: commonTexts.name,
    // Texts come only from addResourceBundle (an empty `resources`, no backend): i18next never loads by itself.
    resources: {},
    // React escapes what it draws, so i18next mustn't escape values a second time.
    interpolation: { escapeValue: false },
  })
  const start = initialLanguage()
  try {
    await switchTo(start)
  } catch (error) {
    if (start === DEFAULT_LANGUAGE) throw error
    console.warn(`Couldn't load ${start}; starting in ${DEFAULT_LANGUAGE}.`, error)
    await switchTo(DEFAULT_LANGUAGE)
  } finally {
    // Pages may load their texts now (in English, at worst, if even the start failed).
    markStarted()
  }
}

// Load `language` and switch it on, unless a later choice came in meanwhile: that one wins, and this one neither
// switches nor reports its own failure. Returns whether `language` was switched on.
async function switchTo(language: Language): Promise<boolean> {
  const mine = ++latestSwitch
  switchingTo = language
  try {
    await prepare(language)
    if (mine !== latestSwitch) return false
    await i18n.changeLanguage(language)
    return true
  } catch (error) {
    if (mine !== latestSwitch) return false
    throw error
  } finally {
    if (mine === latestSwitch) switchingTo = undefined
  }
}

/**
 * Load namespaces' texts in the language on now (and English, the fallback, and a language being switched to), and
 * keep them in step when the language changes. A page's or panel's lazy loader awaits this together with its code,
 * so it's never drawn before its texts are in. Waits for initI18n first. Rejects if a file can't be loaded: the
 * page's error boundary shows it, and its Try again calls this again.
 */
export async function loadNamespaces(...namespaces: AnyNamespace[]): Promise<void> {
  await started
  for (const namespace of namespaces) inUse.add(namespace)
  const languages = new Set([currentLanguage(), switchingTo ?? currentLanguage()])
  await Promise.all([...languages].map((language) => loadTexts(namespaces, language)))
}

/** The language on now (DEFAULT_LANGUAGE before initI18n has run). */
export function currentLanguage(): Language {
  return isLanguage(i18n.language) ? i18n.language : DEFAULT_LANGUAGE
}

/** Headers asking the server for the language on now: the API client and the assistant's stream send them. */
export function languageHeaders(): Record<string, string> {
  return { [ACCEPT_LANGUAGE]: currentLanguage() }
}

/** How the language on now writes numbers and dates, and which way it runs. */
export function currentLanguageInfo(): LanguageInfo {
  return LANGUAGES[currentLanguage()]
}

/** The date picker's locale for the language on now (loaded before the language was switched on). */
export function currentDatePickerLocale(): DayPickerLocale | undefined {
  return datePickerLocales.get(currentLanguage())
}

/**
 * Switch to `next` and save the choice. Resolves once its texts (for every namespace in use) are loaded and every
 * component using them has re-rendered, or once a later choice has replaced it. If they can't be loaded (offline),
 * nothing changes and the promise rejects; calling it again tries again.
 */
export async function setLanguage(next: Language): Promise<void> {
  if (!(await switchTo(next))) return
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, next)
  } catch {
    // Not saved (storage blocked), but still applied for this visit.
  }
}
