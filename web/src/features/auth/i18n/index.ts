// The "auth" namespace: the auth feature's texts. Part of the auth feature (i18n/). Listed in app/_shell/namespaces.ts,
// so it loads when the app boots: the session check in front of the pages and the user menu are part of the frame.

import { defineNamespace } from "@/shared/i18n"

import en from "./en"

/**
 * The auth feature's texts. English is bundled with the app (the session check can always be drawn, even if a file
 * can't be fetched); every other language's file is fetched when first needed.
 */
export const authTexts = defineNamespace("auth", {
  en: () => Promise.resolve({ default: en }),
  hi: () => import("./hi"),
})

/** The auth feature's texts in a component: `const { t } = useTexts()`, then t("signIn.title"), typed. */
export const useTexts = authTexts.useTexts

/** A text explaining why a sign-in failed: its key under "failures". */
export type FailureText = keyof typeof en.failures

// Gives this namespace's keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    auth: typeof en
  }
}
