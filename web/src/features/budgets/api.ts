// The budgets feature's API calls and their types: the only file in this feature that talks to the backend. The
// backend measures the month's spending against each budget (in INR), so the page gets small answers, never every
// expense. Types come from the generated contract; calls go through the shared typed client. Used by queries.ts.

import { api, unwrap, unwrapEmpty, type Schemas } from "@/shared/api/http"

/** A month's spending against the budgets: the overall line, and a line per category (budgeted ones first). */
export type BudgetStatus = Schemas["BudgetStatus"]
/** Spending against one budget; without a budget, only `spent` is set. */
export type BudgetLine = Schemas["BudgetLine"]
/** One category's line: a BudgetLine with the category's id and name. */
export type CategoryBudgetLine = Schemas["CategoryBudgetLine"]
/** Where spending stands against a budget: on track, near the limit, or over it. */
export type BudgetState = Schemas["BudgetState"]

/** Which budget: a category's (its id), or the overall one (null). */
export type BudgetScope = number | null

/** The status of `month` ("YYYY-MM"). `signal` lets TanStack Query cancel it. Throws ApiError if it fails. */
export function getBudgetStatus(month: string, signal?: AbortSignal): Promise<BudgetStatus> {
  return unwrap(api.GET("/api/v1/budgets", { params: { query: { month } }, signal }))
}

/** Sets a budget's monthly limit (rupees, as typed: "8000"). Throws ApiError with the server's reason if refused. */
export function setBudget(scope: BudgetScope, limit: string): Promise<void> {
  const body = { limit }
  if (scope === null) return unwrapEmpty(api.PUT("/api/v1/budgets/overall", { body }))
  const params = { path: { category_id: scope } }
  return unwrapEmpty(api.PUT("/api/v1/budgets/categories/{category_id}", { params, body }))
}

/** Removes a budget. Throws ApiError if it fails (a 404 when there was none). */
export function removeBudget(scope: BudgetScope): Promise<void> {
  if (scope === null) return unwrapEmpty(api.DELETE("/api/v1/budgets/overall"))
  const params = { path: { category_id: scope } }
  return unwrapEmpty(api.DELETE("/api/v1/budgets/categories/{category_id}", { params }))
}
