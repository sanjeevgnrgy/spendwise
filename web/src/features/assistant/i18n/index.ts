// The "assistant" namespace: the assistant feature's texts. Part of the assistant feature (i18n/). Its components
// read them with useTexts(); the chat panel's lazy loader (components/lazy-chat-panel.tsx) loads them with its code.

import { defineNamespace } from "@/shared/i18n"

import type en from "./en"

/** The assistant feature's texts: each language's file is fetched when first needed. */
export const assistantTexts = defineNamespace("assistant", { en: () => import("./en"), hi: () => import("./hi") })

/** The assistant feature's texts in a component: `const { t } = useTexts()`, then t("some.key"), typed. */
export const useTexts = assistantTexts.useTexts

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    assistant: typeof en
  }
}
