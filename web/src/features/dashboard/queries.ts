import { useQuery } from "@tanstack/react-query"

import { getMonthlySummary, getMonthlyTrend } from "./api"

// TanStack Query keys for the Dashboard's totals. Invalidating `all` reloads every one of them.
export const dashboardKeys = {
  all: ["dashboard"] as const,
  summary: (month: string) => [...dashboardKeys.all, "summary", month] as const,
  trend: (months: number) => [...dashboardKeys.all, "trend", months] as const,
}

export function useMonthlySummary(month: string) {
  return useQuery({ queryKey: dashboardKeys.summary(month), queryFn: ({ signal }) => getMonthlySummary(month, signal) })
}

export function useMonthlyTrend(months: number) {
  return useQuery({ queryKey: dashboardKeys.trend(months), queryFn: ({ signal }) => getMonthlyTrend(months, signal) })
}
