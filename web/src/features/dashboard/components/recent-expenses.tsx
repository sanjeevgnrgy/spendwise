import { Link } from "react-router"

import { useCategoryName } from "@/features/categories"
import type { Expense } from "@/features/expenses"
import { EmptyState } from "@/shared/components/empty-state"
import { ROUTES } from "@/shared/config/routes"
import { formatDate, formatMoney } from "@/shared/lib/format"
import { Button } from "@/shared/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

// Already only the latest few: the backend applied the limit.
export function RecentExpenses({ expenses }: { expenses: Expense[] }) {
  const categoryName = useCategoryName()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent expenses</CardTitle>
        <CardDescription>The latest {expenses.length || ""} you recorded</CardDescription>
        <CardAction>
          <Button variant="ghost" size="sm" asChild>
            <Link to={ROUTES.expenses}>View all</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {expenses.length === 0 ? (
          <EmptyState message="No expenses yet." action={{ label: "Add an expense", to: ROUTES.expenses }} />
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
                <span className="shrink-0 font-medium tabular-nums">{formatMoney(expense.amount, expense.currency)}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
