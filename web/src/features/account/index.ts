// The account feature's public API: the app imports ONLY from "@/features/account".
// - SettingsPage: the Settings page (its route file draws it), loaded on first use.
// - accountKeys: so the app's refresh rule (app/_shell/query-client.ts) can reload the sessions and tokens lists.

import { loadNamespaces } from "@/shared/i18n"
import { lazyWithRetry } from "@/shared/lib/lazy-with-retry"

import { accountTexts } from "./i18n"

export { accountKeys } from "./queries"

/**
 * The Settings page, loaded only when it's first shown, together with its texts (in the language on now), so it's
 * never drawn before its words are in. Draw it inside a <Suspense> (app/_frame/app-layout.tsx does). If its code fails
 * to load, the page's error boundary shows the problem, and "Try again" loads it again.
 */
export const SettingsPage = lazyWithRetry(async () => {
  const [{ SettingsPage: page }] = await Promise.all([
    import("./components/settings-page"),
    loadNamespaces(accountTexts),
  ])
  return { default: page }
})
