// The dashboard feature's public API: the app imports ONLY from "@/features/dashboard".
// Every other file in this folder is private, so it can change freely as long as these stay the same.
// - DashboardPage: the Dashboard page (its route file under app/(client)/(app)/ draws it), loaded on first use.
// - dashboardKeys: the cache keys, so app/_shell/query-client.ts can mark the Dashboard's totals out of date.

import { categoriesTexts } from "@/features/categories"
import { loadNamespaces } from "@/shared/i18n"
import { lazyWithRetry } from "@/shared/lib/lazy-with-retry"

import { dashboardTexts } from "./i18n"

export { dashboardKeys } from "./queries"

/**
 * The Dashboard page, loaded only when it's first shown: its code (the charts and their library) is a separate file
 * in the build, so the first paint doesn't wait for it. Its texts ("dashboard", and "categories" for the recent
 * list's category names, in the language on now) load together with it, so it's never drawn before its words are
 * in. The lazy boundary sits here, not in app/, because the app also imports this index for dashboardKeys: a page
 * re-exported from here would always load with it. Draw it inside a <Suspense> (app/_frame/app-layout.tsx does). If
 * its code fails to load, the page's error boundary shows the problem, and "Try again" loads it again.
 */
export const DashboardPage = lazyWithRetry(async () => {
  const [{ DashboardPage: page }] = await Promise.all([
    import("./components/dashboard-page"),
    loadNamespaces(dashboardTexts, categoriesTexts),
  ])
  return { default: page }
})
