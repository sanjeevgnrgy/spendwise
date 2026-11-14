// The dashboard feature's API calls and their types: the only file in this feature that talks to the backend.
// The backend does the adding up (per category, per month), so the Dashboard gets small answers, never every
// expense. Types come from the generated contract; calls go through the shared typed client. Used by queries.ts.

import { api, unwrap, type Schemas } from "@/shared/api/http"

/** One month's totals: the total spent, how many expenses, and the totals by category (biggest first). */
export type MonthlySummary = Schemas["MonthlySummary"]
/** The total spent in each of the last few months, oldest first; a month with nothing spent is there with 0. */
export type MonthlyTrend = Schemas["MonthlyTrend"]

/** The summary of `month` ("YYYY-MM"). `signal` lets TanStack Query cancel it. Throws ApiError if it fails. */
export function getMonthlySummary(month: string, signal?: AbortSignal): Promise<MonthlySummary> {
  return unwrap(api.GET("/api/v1/summary", { params: { query: { month } }, signal }))
}

/** The totals of the last `months` months, up to this one. Throws ApiError if it fails. */
export function getMonthlyTrend(months: number, signal?: AbortSignal): Promise<MonthlyTrend> {
  return unwrap(api.GET("/api/v1/summary/trend", { params: { query: { months } }, signal }))
}
