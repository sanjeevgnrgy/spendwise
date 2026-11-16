// The "account" namespace: the account feature's texts. Part of the account feature (i18n/). Loaded with the Settings
// page, from the feature's lazy loader (index.ts), so the page is never drawn before its words are in.

import { defineNamespace } from "@/shared/i18n"

import type en from "./en"

/** The account feature's texts: each language's file is fetched when first needed. */
export const accountTexts = defineNamespace("account", { en: () => import("./en"), hi: () => import("./hi") })

/** The account feature's texts in a component: `const { t } = useTexts()`, then t("page.title"), typed. */
export const useTexts = accountTexts.useTexts

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    account: typeof en
  }
}
