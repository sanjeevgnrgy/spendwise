// The "budgets" namespace: the budgets feature's texts. Part of the budgets feature (i18n/). Its components read them
// with useTexts(); the Budgets page's lazy loader (the feature's index.ts) loads them with its code.

import { defineNamespace } from "@/shared/i18n"

import type en from "./en"

/** The budgets feature's texts: each language's file is fetched when first needed. */
export const budgetsTexts = defineNamespace("budgets", { en: () => import("./en"), hi: () => import("./hi") })

/** The budgets feature's texts in a component: `const { t } = useTexts()`, then t("some.key"), typed. */
export const useTexts = budgetsTexts.useTexts

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    budgets: typeof en
  }
}
