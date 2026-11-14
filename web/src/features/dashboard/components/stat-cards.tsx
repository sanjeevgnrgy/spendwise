// A component of the dashboard feature: the row of three stat cards at the top of the Dashboard. Used by the
// Dashboard page.

import { formatMoney, formatMonth, plural } from "@/shared/lib/format"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

import type { MonthlySummary } from "../api"

/**
 * Three headline numbers for the current month, all straight from the backend's summary: the total spent, how many
 * expenses (and categories used), and the top category with its total.
 */
export function StatCards({ summary }: { summary: MonthlySummary }) {
  const top = summary.by_category[0] // the list comes biggest first
  const monthName = formatMonth(summary.month)

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardDescription>Spent in {monthName}</CardDescription>
          <CardTitle className="text-3xl tabular-nums">{formatMoney(summary.total, summary.currency)}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {summary.expense_count === 0 ? "No expenses yet this month" : "Total of this month's expenses"}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Expenses this month</CardDescription>
          <CardTitle className="text-3xl tabular-nums">{summary.expense_count}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {plural(summary.by_category.length, "category", "categories")} used
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Top category</CardDescription>
          <CardTitle className="text-3xl">{top ? top.category_name : "—"}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {top
            ? `${formatMoney(top.total, summary.currency)} across ${plural(top.expense_count, "expense")}`
            : "Nothing spent yet"}
        </CardContent>
      </Card>
    </div>
  )
}
