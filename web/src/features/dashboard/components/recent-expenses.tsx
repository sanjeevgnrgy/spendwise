// A component of the dashboard feature: the "Recent expenses" card. Used by the Dashboard page, which loads the
// newest few through the expenses feature's useExpenses.

import Link from "next/link"

import { useCategoryName } from "@/features/categories"
import type { Expense } from "@/features/expenses"
import { EmptyState } from "@/shared/components/empty-state"
import { ROUTES } from "@/shared/config/routes"
import { formatDate, formatMoney } from "@/shared/lib/format"
import { Button } from "@/shared/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

import { useTexts } from "../i18n"

/**
 * "Recent expenses": the newest few, each with its merchant, category, date and amount, and a "View all" link to the
 * Expenses page. `expenses` is already only the latest few (the backend applied the limit). With none, it says so
 * and offers a link to add one.
 */
export function RecentExpenses({ expenses }: { expenses: Expense[] }) {
  const { t } = useTexts()
  const categoryName = useCategoryName()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("recent.title")}</CardTitle>
        <CardDescription>{t("recent.latest", { count: expenses.length })}</CardDescription>
        <CardAction>
          <Button variant="ghost" size="sm" asChild>
            <Link href={ROUTES.expenses}>{t("recent.viewAll")}</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {expenses.length === 0 ? (
          <EmptyState message={t("recent.empty")} action={{ label: t("addExpense"), to: ROUTES.expenses }} />
        ) : (
          <ul className="divide-y">
            {expenses.map((expense) => (
              <li key={expense.id} className="flex items-center justify-between gap-4 py-2.5">
                <div className="min-w-0">
                  <p className="truncate font-medium">{expense.merchant}</p>
                  <p className="text-sm text-muted-foreground">
                    {categoryName(expense.category_id)} · {formatDate(expense.spent_on)}
                  </p>
                </div>
                <span className="shrink-0 font-medium tabular-nums">
                  {formatMoney(expense.amount, expense.currency)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
