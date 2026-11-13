import { useEffect, useState } from "react"
import { toast } from "sonner"

import {
  createExpense,
  deleteExpense,
  listCategories,
  listExpenses,
  updateExpense,
  type Category,
  type Expense,
  type ExpenseChanges,
  type ExpenseFilters,
  type NewExpense,
} from "@/api"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { formatDate, formatMoney } from "@/lib/format"
import { AddExpenseDialog } from "@/pages/expenses/add-expense-dialog"
import { ExpensesTable } from "@/pages/expenses/expenses-table"
import { FiltersBar } from "@/pages/expenses/filters-bar"

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

// The page owns the data (expenses, categories, filters) and every call that changes it.
// Its children only display things and report what the user did, through props.
export function ExpensesPage() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [filters, setFilters] = useState<ExpenseFilters>({})
  const [loading, setLoading] = useState(true)
  // Bumping this number re-runs the "load expenses" effect below, i.e. "reload the list".
  const [reloadCount, setReloadCount] = useState(0)
  // The expenses waiting for "are you sure?"; null means the confirmation dialog is closed.
  const [pendingDelete, setPendingDelete] = useState<Expense[] | null>(null)

  // Load the categories once, when the page first appears ([] = no dependencies, run once).
  useEffect(() => {
    listCategories()
      .then(setCategories)
      .catch((error) => toast.error(messageOf(error)))
  }, [])

  // Load the expenses whenever the filters change (or a reload is asked for).
  useEffect(() => {
    let cancelled = false
    // Wait 300 ms after the last change, so typing in Search doesn't call the API on every key.
    const timer = setTimeout(() => {
      setLoading(true)
      listExpenses(filters)
        .then((rows) => {
          if (!cancelled) setExpenses(rows)
        })
        .catch((error) => {
          if (!cancelled) toast.error(messageOf(error))
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 300)
    // Clean-up: runs before the next run of this effect. It cancels the pending timer and makes
    // sure an older, slower response can't overwrite the results of a newer filter.
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [filters, reloadCount])

  const reload = () => setReloadCount((count) => count + 1)

  async function handleAdd(expense: NewExpense): Promise<boolean> {
    try {
      await createExpense(expense)
      toast.success("Expense added")
      reload()
      return true
    } catch (error) {
      // e.g. "Amount must be greater than 0", straight from the backend's business rules.
      toast.error(messageOf(error))
      return false
    }
  }

  async function handleSave(id: number, changes: ExpenseChanges): Promise<boolean> {
    if (Object.keys(changes).length === 0) return true // nothing changed: just leave edit mode
    try {
      await updateExpense(id, changes)
      toast.success("Expense updated")
      reload()
      return true
    } catch (error) {
      toast.error(messageOf(error))
      return false
    }
  }

  async function handleConfirmDelete() {
    const toDelete = pendingDelete ?? []
    setPendingDelete(null)
    // allSettled (not all): one failure shouldn't hide whether the others were deleted.
    const results = await Promise.allSettled(toDelete.map((expense) => deleteExpense(expense.id)))
    const failures = results.filter((result) => result.status === "rejected")
    const deleted = toDelete.length - failures.length
    if (deleted > 0) toast.success(deleted === 1 ? "Expense deleted" : `${deleted} expenses deleted`)
    if (failures.length > 0) {
      toast.error(`Couldn't delete ${failures.length}: ${messageOf((failures[0] as PromiseRejectedResult).reason)}`)
    }
    reload()
  }

  const single = pendingDelete?.length === 1 ? pendingDelete[0] : null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Expenses</h1>
          <p className="text-sm text-muted-foreground">Add, find, edit and delete your expenses.</p>
        </div>
        <AddExpenseDialog categories={categories} onAdd={handleAdd} />
      </div>

      <FiltersBar categories={categories} filters={filters} onChange={setFilters} />

      {/* setPendingDelete is passed directly: React keeps it the same between renders,
          so the table doesn't rebuild its columns every time this page re-renders. */}
      <ExpensesTable
        expenses={expenses}
        categories={categories}
        loading={loading}
        onSave={handleSave}
        onDelete={setPendingDelete}
      />

      <AlertDialog open={pendingDelete !== null} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {single ? "Delete this expense?" : `Delete ${pendingDelete?.length ?? 0} expenses?`}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {single &&
                `${single.merchant}, ${formatMoney(single.amount, single.currency)} on ${formatDate(single.spent_on)}. `}
              This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={handleConfirmDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
