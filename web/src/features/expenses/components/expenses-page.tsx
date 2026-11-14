// A component of the expenses feature: the Expenses page, the feature's main export (app/pages.tsx routes to it).
// It holds the page's state (the filters, and which expenses are waiting for "are you sure?"), loads the list
// through useExpenses, and lays out its parts: the Add dialog, the filters bar, the table, and the delete dialog.

import { useState } from "react"

import { RefreshNotice } from "@/shared/components/refresh-notice"
import { SectionError } from "@/shared/components/section-error"
import { useDebouncedValue } from "@/shared/hooks/use-debounced-value"
import { messageOf } from "@/shared/lib/errors"

import type { Expense, ExpenseFilters } from "../api"
import { useExpenses } from "../queries"
import { AddExpenseDialog } from "./dialogs/add-expense-dialog"
import { DeleteExpensesDialog } from "./dialogs/delete-expenses-dialog"
import { ExpensesTable } from "./table/expenses-table"
import { FiltersBar } from "./filters/filters-bar"

// Wait this long after the last change before asking the API, so typing in Search doesn't send a
// request on every key.
const FILTER_DEBOUNCE_MS = 300

// What the table gets while nothing is loaded: one array, the same on every render. A new `[]` each time would
// count as new data, and the table clears its selection whenever its data changes. Never modified.
const NO_EXPENSES: Expense[] = []

/**
 * The Expenses page: a title with the Add button, the filters, the table, and the delete confirmation. If
 * nothing could be loaded, an error card with Try again takes the table's place; if a reload fails, the rows
 * stay and a "couldn't refresh" notice appears above them.
 */
export function ExpensesPage() {
  const [filters, setFilters] = useState<ExpenseFilters>({})
  // The expenses waiting for "are you sure?"; null means the confirmation dialog is closed.
  const [pendingDelete, setPendingDelete] = useState<Expense[] | null>(null)
  // TanStack Query loads (and caches) the list, cancels outdated requests, and reloads it whenever
  // something changes expenses: this page's dialogs, or the assistant. The filters bar shows each change at
  // once; the query only sees the filters once they've stopped changing.
  const expenses = useExpenses(useDebouncedValue(filters, FILTER_DEBOUNCE_MS))

  // An error card only if nothing could be loaded; if a reload failed, keep the rows and say so above them.
  // setPendingDelete goes to the table as it is: React keeps it the same between renders, so the table
  // doesn't rebuild its columns every time this page re-renders.
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Expenses</h1>
          <p className="text-sm text-muted-foreground">Add, find, edit and delete your expenses.</p>
        </div>
        <AddExpenseDialog />
      </div>

      <FiltersBar filters={filters} onChange={setFilters} />

      {expenses.isError && expenses.data && (
        <RefreshNotice message={messageOf(expenses.error)} onRetry={() => expenses.refetch()} retrying={expenses.isFetching} />
      )}
      {expenses.isError && !expenses.data ? (
        <SectionError
          title="Couldn't load your expenses"
          message={messageOf(expenses.error)}
          onRetry={() => expenses.refetch()}
          retrying={expenses.isFetching}
        />
      ) : (
        <ExpensesTable
          expenses={expenses.data?.items ?? NO_EXPENSES}
          total={expenses.data?.total ?? 0}
          loading={expenses.isPending}
          onDelete={setPendingDelete}
        />
      )}

      <DeleteExpensesDialog expenses={pendingDelete} onClose={() => setPendingDelete(null)} />
    </div>
  )
}
