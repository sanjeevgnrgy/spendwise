// The "common" namespace: the texts shared/ shows. Part of shared/i18n. initI18n always loads it when the app boots,
// and it's the default namespace, so shared components call useTranslation() without naming one.

import { defineNamespace } from "../namespace"
import en from "./en"

/**
 * The shared texts. English is bundled with the app (the frame can always be drawn, even if a file can't be
 * fetched); every other language's file is fetched when first needed.
 */
export const commonTexts = defineNamespace("common", {
  en: () => Promise.resolve({ default: en }),
  hi: () => import("./hi"),
})

/** The shape of the common texts (its keys), for code that names one by a variable. */
export type CommonTexts = typeof en

// Gives t("theme.light") and the other common keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    common: typeof en
  }
}
