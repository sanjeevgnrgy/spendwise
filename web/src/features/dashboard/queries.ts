// The dashboard feature's server state, through TanStack Query: the cache keys and a hook per request. Used by
// the Dashboard page; `dashboardKeys` is also public (index.ts), so the app's refresh rule can mark the totals out
// of date whenever expenses change.

import { useQuery } from "@tanstack/react-query"

import { getMonthlySummary, getMonthlyTrend } from "./api"

/**
 * TanStack Query keys for the Dashboard's totals, all filed under ["dashboard", ...]. Marking `all` out of date
 * (app/query-client.ts does, after any expense change) reloads every one of them.
 */
export const dashboardKeys = {
  all: ["dashboard"] as const,
  // One key per month and per trend length, so each is cached on its own.
  summary: (month: string) => [...dashboardKeys.all, "summary", month] as const,
  trend: (months: number) => [...dashboardKeys.all, "trend", months] as const,
}

/** The totals of `month` ("YYYY-MM"), cached per month. Returns TanStack Query's result (`data`, `isError`...). */
export function useMonthlySummary(month: string) {
  return useQuery({ queryKey: dashboardKeys.summary(month), queryFn: ({ signal }) => getMonthlySummary(month, signal) })
}

/** The totals of the last `months` months, cached per length. Returns TanStack Query's result. */
export function useMonthlyTrend(months: number) {
  return useQuery({ queryKey: dashboardKeys.trend(months), queryFn: ({ signal }) => getMonthlyTrend(months, signal) })
}
