import { api, unwrap, type Schemas } from "@/shared/api/http"

export type MonthlySummary = Schemas["MonthlySummary"]
export type MonthlyTrend = Schemas["MonthlyTrend"]

export function getMonthlySummary(month: string, signal?: AbortSignal): Promise<MonthlySummary> {
  return unwrap(api.GET("/api/v1/summary", { params: { query: { month } }, signal }))
}

export function getMonthlyTrend(months: number, signal?: AbortSignal): Promise<MonthlyTrend> {
  return unwrap(api.GET("/api/v1/summary/trend", { params: { query: { months } }, signal }))
}
