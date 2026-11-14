// A hook of the expenses feature: the expenses table's inline editing. Which row is open for editing, saving an
// edit (through useUpdateExpense, with its toasts), and which row's save is running. Used by expenses-table.tsx,
// which draws the open row as an EditRow and gives `start` to the columns' Edit buttons.

import { useState } from "react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"

import type { ExpenseChanges } from "../api"
import { useSavingExpenseIds, useUpdateExpense } from "../queries"

/** What useExpenseEditor returns: the open row, and what can be done with it. */
export interface ExpenseEditor {
  /** The expense whose row is in edit mode; null when none is. */
  editingId: number | null
  /** Opens this expense's row for editing (closing any other). The same function on every render. */
  start: (id: number) => void
  /** Closes the row being edited, keeping nothing of the draft. */
  cancel: () => void
  /** Saves one row's changes; with no changes it only closes the row. */
  save: (id: number, changes: ExpenseChanges) => void
  /** Whether this expense's save is in flight (only that row shows it's busy). */
  isSaving: (id: number) => boolean
}

/**
 * The table's inline editing, one row at a time. A row stays open until its save succeeds: then a toast says
 * "Expense updated" and the row closes. If the save fails, a toast gives the backend's reason and the row stays
 * open with what you typed, ready to fix.
 */
export function useExpenseEditor(): ExpenseEditor {
  const [editingId, setEditingId] = useState<number | null>(null)
  const update = useUpdateExpense()
  const savingIds = useSavingExpenseIds()

  // Leave edit mode for this row only: another row may have been opened while this one was saving.
  const close = (id: number) => setEditingId((open) => (open === id ? null : open))

  function save(id: number, changes: ExpenseChanges) {
    if (Object.keys(changes).length === 0) return close(id) // nothing changed: just leave edit mode
    // mutateAsync, not mutate with callbacks: TanStack Query only calls mutate()'s own callbacks for the latest
    // call, so a row saved while another row was still saving would lose its toast (and a failure would be silent).
    // Each mutateAsync call has its own promise, so every save gets its own answer.
    void update.mutateAsync({ id, changes }).then(
      () => {
        toast.success("Expense updated")
        close(id)
      },
      (error: unknown) => toast.error(messageOf(error)),
    )
  }

  return {
    editingId,
    // React's state setter never changes, so the table's columns (which use it) aren't rebuilt on every render.
    start: setEditingId,
    cancel: () => setEditingId(null),
    save,
    // Every running update counts (useSavingExpenseIds), so each row that's saving shows it, not only the latest.
    isSaving: (id) => savingIds.includes(id),
  }
}
