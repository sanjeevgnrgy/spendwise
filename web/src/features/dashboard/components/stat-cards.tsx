// A component of the dashboard feature: the row of three stat cards at the top of the Dashboard. Used by the
// Dashboard page.

import { formatMoney, formatMonth } from "@/shared/lib/format"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

import type { MonthlySummary } from "../api"
import { useTexts } from "../i18n"

/**
 * Three headline numbers for the current month, all straight from the backend's summary: the total spent, how many
 * expenses (and categories used), and the top category with its total.
 */
export function StatCards({ summary }: { summary: MonthlySummary }) {
  const { t } = useTexts()
  const top = summary.by_category[0] // the list comes biggest first
  const monthName = formatMonth(summary.month)

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardDescription>{t("stats.spentIn", { month: monthName })}</CardDescription>
          <CardTitle className="text-3xl tabular-nums">{formatMoney(summary.total, summary.currency)}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {summary.expense_count === 0 ? t("stats.noExpensesThisMonth") : t("stats.totalOfMonth")}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>{t("stats.expensesThisMonth")}</CardDescription>
          <CardTitle className="text-3xl tabular-nums">{summary.expense_count}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {t("stats.categoriesUsed", { count: summary.by_category.length })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>{t("stats.topCategory")}</CardDescription>
          <CardTitle className="text-3xl">{top ? top.category_name : "—"}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {top
            ? t("stats.topAcross", { amount: formatMoney(top.total, summary.currency), count: top.expense_count })
            : t("stats.nothingSpent")}
        </CardContent>
      </Card>
    </div>
  )
}
