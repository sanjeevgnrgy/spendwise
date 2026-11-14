// What one namespace of texts is: its name, and how to load it in each language. Part of shared/i18n. Every
// namespace defines itself with defineNamespace (in its owner's i18n/index.ts). Shared/'s and the app frame's are
// loaded when the app boots (initI18n); a page's or panel's when it's first opened (loadNamespaces, from its lazy
// loader).

import type { FlatNamespace } from "i18next"
import { useTranslation } from "react-i18next"

import type { DEFAULT_LANGUAGE, Language } from "./languages"

/** A namespace's texts: strings, grouped by area. Keys are written in camelCase; a group is a nested object. */
export interface Texts {
  [key: string]: string | Texts
}

// The plural forms Unicode's CLDR knows. i18next picks one with Intl.PluralRules and adds it to the key as a
// suffix ("count_one", "count_other"), so a text that counts has one key per form its language uses.
type PluralCategory = "zero" | "one" | "two" | "few" | "many" | "other"

/**
 * Another language's version of a namespace's English texts: the same keys (a missing or misspelt key is a type
 * error), each with any wording. A language with more plural forms than English may add them ("count_few").
 */
export type Translation<T> = { [K in keyof T]: T[K] extends string ? string : Translation<T[K]> } & {
  [key: `${string}_${PluralCategory}`]: string
}

/** Every language except English. */
export type OtherLanguage = Exclude<Language, typeof DEFAULT_LANGUAGE>

/**
 * A loader per language: a dynamic import of that language's file (its default export), so every file, English
 * included, is a separate chunk fetched only when needed. English's file sets the type every other one must match.
 */
export type TranslationLoaders<T> = { readonly [L in typeof DEFAULT_LANGUAGE]: () => Promise<{ default: T }> } & {
  readonly [L in OtherLanguage]: () => Promise<{ default: NoInfer<Translation<T>> }>
}

/** One namespace: its name and a loader for every language. */
export interface Namespace<Name extends string = string, T extends Texts = Texts> {
  readonly name: Name
  readonly load: TranslationLoaders<T>
}

/** Any namespace, whatever its keys: what the loading code (i18n.ts) works with. */
export interface AnyNamespace {
  readonly name: string
  readonly load: { readonly [L in Language]: () => Promise<{ default: Texts }> }
}

/** A defined namespace, with the hook its components read it through. */
export interface DefinedNamespace<Name extends FlatNamespace, T extends Texts> extends Namespace<Name, T> {
  /** The namespace's texts in a component: `const { t } = useTexts()`, then t("group.key"), typed by its en.ts. */
  readonly useTexts: () => ReturnType<typeof useTranslation<Name>>
}

/**
 * Define a namespace. `load` must name every language in LANGUAGES, so a new language can't be forgotten in one
 * namespace. `name` must have a ResourceNamespaceMap entry, which gives the namespace's keys their type from the
 * English file: `declare module "i18next" { interface ResourceNamespaceMap { expenses: typeof en } }`, with
 * `import type en from "./en"` (a type-only import, so the English texts stay out of the importing chunk).
 */
export function defineNamespace<const Name extends FlatNamespace, T extends Texts>(
  name: Name,
  load: TranslationLoaders<T>,
): DefinedNamespace<Name, T> {
  return { name, load, useTexts: () => useTranslation(name) }
}
