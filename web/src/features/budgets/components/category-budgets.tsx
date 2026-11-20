// A component of the budgets feature: the "By category" card: one row per category, with its limit's bar or what
// was spent, and its own Set or Change limit button. Used by the Budgets page.

import { EmptyState } from "@/shared/components/empty-state"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

import type { BudgetStatus, CategoryBudgetLine } from "../api"
import { useTexts } from "../i18n"
import { BudgetDialog } from "./budget-dialog"
import { BudgetFigures } from "./budget-figures"
import { BudgetStateBadge } from "./budget-state-badge"

/** Every category, in the server's order (budgeted first, closest to its limit at the top). */
export function CategoryBudgets({ status }: { status: BudgetStatus }) {
  const { t } = useTexts()
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("categories.title")}</CardTitle>
        <CardDescription>{t("categories.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        {status.categories.length === 0 ? (
          <EmptyState message={t("categories.empty")} />
        ) : (
          <ul className="divide-y">
            {status.categories.map((line) => (
              <CategoryRow key={line.category_id} line={line} currency={status.currency} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

/** One category: its name and state, its button, and its figures. */
function CategoryRow({ line, currency }: { line: CategoryBudgetLine; currency: string }) {
  return (
    <li className="grid gap-2 py-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-medium">{line.category_name}</span>
          {line.state && <BudgetStateBadge state={line.state} />}
        </div>
        <BudgetDialog scope={line.category_id} name={line.category_name} currentLimit={line.limit ?? null} />
      </div>
      <BudgetFigures line={line} currency={currency} name={line.category_name} />
    </li>
  )
}
