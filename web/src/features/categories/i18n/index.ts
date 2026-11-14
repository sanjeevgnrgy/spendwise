// The "categories" namespace: the categories feature's texts (the category dropdown). Part of the categories feature
// (i18n/). Its components read them with useTexts(). A page that draws CategorySelect loads them with its own
// (the Expenses page's lazy loader), through categoriesTexts in the feature's index.ts.

import { defineNamespace } from "@/shared/i18n"

import type en from "./en"

/** The categories feature's texts: each language's file is fetched when first needed. */
export const categoriesTexts = defineNamespace("categories", { en: () => import("./en"), hi: () => import("./hi") })

/** The categories feature's texts in a component: `const { t } = useTexts()`, then t("select.loading"), typed. */
export const useTexts = categoriesTexts.useTexts

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    categories: typeof en
  }
}
