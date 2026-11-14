// The "expenses" namespace: the expenses feature's texts. Part of the expenses feature (i18n/). Its components read
// them with useTexts(); the Expenses page's lazy loader (the feature's index.ts) loads them with its code.

import { defineNamespace } from "@/shared/i18n"

import type en from "./en"

/** The expenses feature's texts: each language's file is fetched when first needed. */
export const expensesTexts = defineNamespace("expenses", { en: () => import("./en"), hi: () => import("./hi") })

/** The expenses feature's texts in a component: `const { t } = useTexts()`, then t("page.title"), typed. */
export const useTexts = expensesTexts.useTexts

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    expenses: typeof en
  }
}
