// The expenses feature's public API: other features and the app import ONLY from "@/features/expenses".
// Every other file in this folder is private, so it can change freely as long as these stay the same.
// - Expense: one expense's type (the Dashboard's recent list draws it).
// - ExpensesPage: the Expenses page (its route file under app/(client)/(app)/ draws it), loaded on first use.
// - expenseKeys: the cache keys, so app/_shell/query-client.ts can mark every expense list out of date.
// - useExpenses: a filtered list of expenses (the Dashboard shows the newest few with it).

import { categoriesTexts } from "@/features/categories"
import { loadNamespaces } from "@/shared/i18n"
import { lazyWithRetry } from "@/shared/lib/lazy-with-retry"

import { expensesTexts } from "./i18n"

export type { Expense } from "./api"
export { expenseKeys, useExpenses } from "./queries"

/**
 * The Expenses page, loaded only when it's first shown: its code (the table, dialogs, filters) is a separate
 * file in the build, so opening the app doesn't wait for it. Its texts load together with it, in the language on
 * now: the feature's own and the categories feature's (the page draws CategorySelect). The lazy boundary sits
 * here, not in app/, because the app also imports this index for expenseKeys: a page re-exported from here would
 * always load with it.
 * Draw it inside a <Suspense> (app/_frame/app-layout.tsx does). If its code fails to load, the page's error
 * boundary shows the problem, and "Try again" loads it again.
 */
export const ExpensesPage = lazyWithRetry(async () => {
  const [{ ExpensesPage: page }] = await Promise.all([
    import("./components/expenses-page"),
    loadNamespaces(expensesTexts, categoriesTexts),
  ])
  return { default: page }
})
