// A component of the expenses feature: the "are you sure?" dialog before deleting one expense or several. It
// runs the delete and reports what happened. Used by the Expenses page, which opens it from the table's buttons.

import { useState } from "react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"
import { formatDate, formatMoney, plural } from "@/shared/lib/format"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/ui/alert-dialog"

import type { Expense } from "../api"
import { useDeleteExpenses } from "../queries"

interface DeleteExpensesDialogProps {
  /** The expenses to delete; null while the dialog is closed. */
  expenses: Expense[] | null
  /** Closes the dialog (Cancel, Escape, a click outside, or Delete, which closes it first). */
  onClose: () => void
}

/**
 * "Are you sure?" before deleting one expense or several: a delete can't be undone. Open while `expenses` isn't
 * null. For one expense it names it (merchant, amount, date); for several it counts them. Delete closes the
 * dialog at once and deletes in the background, then toasts how many were deleted and, separately, how many
 * couldn't be (with the first reason): a partial success shows both.
 */
export function DeleteExpensesDialog({ expenses, onClose }: DeleteExpensesDialogProps) {
  const remove = useDeleteExpenses()
  // What the dialog shows. It keeps the last list while it fades out after closing, so the text doesn't
  // flash "Delete 0 expenses?" (React's "adjust state when a prop changes" pattern, during render).
  const [shown, setShown] = useState<Expense[]>(expenses ?? [])
  if (expenses !== null && expenses !== shown) setShown(expenses)
  // One expense is named in the text; several are only counted.
  const single = shown.length === 1 ? shown[0] : null

  // Close first, then delete. While the delete runs, the table disables its delete buttons (it watches this
  // mutation, through useIsDeletingExpenses), so the same rows can't be sent for deleting twice.
  function confirm() {
    const ids = shown.map((expense) => expense.id)
    onClose()
    // Only onSuccess: the mutation resolves even when some deletes fail, and lists the failures (useDeleteExpenses).
    remove.mutate(ids, {
      onSuccess: ({ deleted, failures }) => {
        if (deleted > 0) toast.success(deleted === 1 ? "Expense deleted" : `${plural(deleted, "expense")} deleted`)
        if (failures.length > 0) toast.error(`Couldn't delete ${failures.length}: ${messageOf(failures[0])}`)
      },
    })
  }

  return (
    <AlertDialog open={expenses !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{single ? "Delete this expense?" : `Delete ${plural(shown.length, "expense")}?`}</AlertDialogTitle>
          <AlertDialogDescription>
            {single && `${single.merchant}, ${formatMoney(single.amount, single.currency)} on ${formatDate(single.spent_on)}. `}
            This can't be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={confirm}>
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
