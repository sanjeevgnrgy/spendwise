// The "app" namespace: the texts of the app's frame. Part of the app composition (app/_i18n/). Listed in
// app/_shell/namespaces.ts, so it's loaded when the app boots, before the first paint.

import { defineNamespace } from "@/shared/i18n"

import en from "./en"

/**
 * The app frame's texts. English is bundled with the app (the frame can always be drawn, even if a file can't be
 * fetched); every other language's file is fetched when first needed.
 */
export const appTexts = defineNamespace("app", {
  en: () => Promise.resolve({ default: en }),
  hi: () => import("./hi"),
})

/** The app frame's texts in a component: `const { t } = useTexts()`, then t("pages.dashboard"), typed. */
export const useTexts = appTexts.useTexts

/** A page's name: its key under "pages" (and, for a page still to come, under "comingSoon"). */
export type PageName = keyof typeof en.pages
/** A page that isn't built yet: it also has a "comingSoon" text. */
export type ComingSoonName = keyof typeof en.comingSoon

// Gives t("pages.dashboard") and the other app keys their types (a misspelt key is a compile error).
declare module "i18next" {
  interface ResourceNamespaceMap {
    app: typeof en
  }
}
