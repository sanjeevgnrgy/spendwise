// The "dashboard" namespace: the dashboard feature's texts. Part of the dashboard feature (i18n/). Its components
// read them with useTexts(); the Dashboard page's lazy loader (the feature's index.ts) loads them with its code.

import { defineNamespace } from "@/shared/i18n"

import type en from "./en"

/** The dashboard feature's texts: each language's file is fetched when first needed. */
export const dashboardTexts = defineNamespace("dashboard", { en: () => import("./en"), hi: () => import("./hi") })

/** The dashboard feature's texts in a component: `const { t } = useTexts()`, then t("some.key"), typed. */
export const useTexts = dashboardTexts.useTexts

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    dashboard: typeof en
  }
}
