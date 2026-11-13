import { Link } from "react-router"

import type { Category, Expense } from "@/api"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDate, formatMoney } from "@/lib/format"
import { EmptyState } from "@/pages/dashboard/empty-state"

interface RecentExpensesProps {
  expenses: Expense[] // already only the latest few: the backend applied the limit
  categories: Category[]
}

export function RecentExpenses({ expenses, categories }: RecentExpensesProps) {
  const categoryNames = new Map(categories.map((c) => [c.id, c.name]))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent expenses</CardTitle>
        <CardDescription>The latest {expenses.length || ""} you recorded</CardDescription>
        <CardAction>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/expenses">View all</Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {expenses.length === 0 ? (
          <EmptyState message="No expenses yet." />
        ) : (
          <ul className="divide-y">
            {expenses.map((expense) => (
              <li key={expense.id} className="flex items-center justify-between gap-4 py-2.5">
                <div className="min-w-0">
                  <p className="truncate font-medium">{expense.merchant}</p>
                  <p className="text-sm text-muted-foreground">
                    {categoryNames.get(expense.category_id) ?? "Unknown"} · {formatDate(expense.spent_on)}
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
