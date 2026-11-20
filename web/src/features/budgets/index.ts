// The budgets feature's public API: the app and other features import ONLY from "@/features/budgets".
// Every other file in this folder is private, so it can change freely as long as these stay the same.
// - BudgetsPage: the Budgets page (its route file under app/(client)/(app)/budgets/ draws it), loaded on first use.
// - budgetKeys: the cache keys, so app/_shell/query-client.ts can mark the budgets out of date.
// - useBudgetStatus, BudgetMeter: what the Dashboard's budget card uses (the status, and the bar, which has no texts
//   of its own: the card gives its label).

import { loadNamespaces } from "@/shared/i18n"
import { lazyWithRetry } from "@/shared/lib/lazy-with-retry"

import { budgetsTexts } from "./i18n"

export type { BudgetStatus } from "./api"
export { BudgetMeter } from "./components/budget-meter"
export { budgetKeys, useBudgetStatus } from "./queries"

/**
 * The Budgets page, loaded only when it's first shown: its code is a separate file in the build, and its texts load
 * together with it, in the language on now, so it's never drawn before its words are in. Draw it inside a
 * <Suspense> (app/_frame/app-layout.tsx does). If its code fails to load, the page's error boundary shows the
 * problem, and "Try again" loads it again.
 */
export const BudgetsPage = lazyWithRetry(async () => {
  const [{ BudgetsPage: page }] = await Promise.all([import("./components/budgets-page"), loadNamespaces(budgetsTexts)])
  return { default: page }
})
