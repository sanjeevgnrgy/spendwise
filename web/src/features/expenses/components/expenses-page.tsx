import { useState } from "react"

import { RefreshNotice } from "@/shared/components/refresh-notice"
import { SectionError } from "@/shared/components/section-error"
import { useDebouncedValue } from "@/shared/hooks/use-debounced-value"
import { messageOf } from "@/shared/lib/errors"

import type { Expense, ExpenseFilters } from "../api"
import { useExpenses } from "../queries"
import { AddExpenseDialog } from "./add-expense-dialog"
import { DeleteExpensesDialog } from "./delete-expenses-dialog"
import { ExpensesTable } from "./expenses-table"
import { FiltersBar } from "./filters-bar"

// Wait this long after the last change before asking the API, so typing in Search doesn't send a
// request on every key.
const FILTER_DEBOUNCE_MS = 300

export function ExpensesPage() {
  const [filters, setFilters] = useState<ExpenseFilters>({})
  // The expenses waiting for "are you sure?"; null means the confirmation dialog is closed.
  const [pendingDelete, setPendingDelete] = useState<Expense[] | null>(null)
  // TanStack Query loads (and caches) the list, cancels outdated requests, and reloads it whenever
  // something changes expenses: this page's dialogs, or the assistant.
  const expenses = useExpenses(useDebouncedValue(filters, FILTER_DEBOUNCE_MS))

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

      {/* An error card only if nothing could be loaded; if a reload failed, keep the rows and say so. */}
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
        // setPendingDelete is passed directly: React keeps it the same between renders, so the table
        // doesn't rebuild its columns every time this page re-renders.
        <ExpensesTable
          expenses={expenses.data?.items ?? []}
          total={expenses.data?.total ?? 0}
          loading={expenses.isPending}
          onDelete={setPendingDelete}
        />
      )}

      <DeleteExpensesDialog expenses={pendingDelete} onClose={() => setPendingDelete(null)} />
    </div>
  )
}
