// A component of the expenses feature: one table row in "edit mode", with an input or dropdown in each cell
// and Save / Cancel buttons. Used by expenses-table.tsx, which draws it in place of the row being edited; the
// saving itself is done by the table's editor (use-expense-editor.ts).

import { Check, X } from "lucide-react"
import { useState, type KeyboardEvent } from "react"

import { CategorySelect } from "@/features/categories"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { TableCell, TableRow } from "@/shared/ui/table"

import type { Expense, ExpenseChanges } from "../../api"
import { changesBetween, draftOf } from "../../expense-form"
import { useExpenseDraft, type ExpenseDraftState } from "../../use-expense-draft"
import { PaymentMethodSelect } from "../fields/payment-method-select"

interface EditRowProps {
  /** The expense to edit, as the table has it now. */
  expense: Expense
  /** This row's save is in flight: Save and Cancel wait. */
  saving: boolean
  /** Save: gets only the changed fields ({} if nothing changed). */
  onSave: (changes: ExpenseChanges) => void
  /** Cancel (the button, or Escape in a text box). */
  onCancel: () => void
}

/**
 * One table row in "edit mode". It must render the same columns, in the same order, as the
 * table's columns (expense-columns.tsx): select, id, date, merchant, category, amount, paid with, note, actions.
 *
 * Enter in a text box saves and Escape cancels. While this row's save is in flight, the Save and Cancel buttons
 * are disabled and Enter does nothing. The row doesn't call the API itself: Save hands the table only the fields
 * you changed.
 */
export function EditRow({ expense: current, saving, onSave, onCancel }: EditRowProps) {
  // The expense as it was when editing started. If the list reloads meanwhile (say the assistant changed
  // this expense), Save still compares the draft with what you started from, so it only sends the fields
  // YOU changed, and never quietly undoes someone else's change.
  const [expense] = useState(current)
  // A private draft of the values while editing. The table's data only changes after Save succeeds,
  // so Cancel can simply throw the draft away.
  const { draft, setField } = useExpenseDraft(() => draftOf(current))
  // Every control says which expense it edits, for screen readers ("Merchant of #14").
  const of = (field: string) => `${field} of #${expense.id}`

  function save() {
    // Enter can fire again (or repeat while held) before the first save finishes: send it once.
    if (!saving) onSave(changesBetween(expense, draft))
  }

  // Enter saves and Escape cancels, but only while typing in a text box (dropdowns use those keys themselves).
  function handleKeyDown(event: KeyboardEvent) {
    if (!(event.target instanceof HTMLInputElement)) return
    // While an input method (e.g. for Hindi or Japanese) is composing, Enter picks the suggested text.
    if (event.nativeEvent.isComposing) return
    if (event.key === "Enter") save()
    if (event.key === "Escape") onCancel()
  }

  // The first cell stays empty: it's the select column, and a row being edited has no checkbox. The id can't be
  // edited (it's how the expense is found), so it's shown as text.
  return (
    <TableRow className="bg-muted/50" onKeyDown={handleKeyDown}>
      <TableCell />
      <TableCell className="text-muted-foreground tabular-nums">#{expense.id}</TableCell>
      <EditFieldCells draft={draft} setField={setField} of={of} />
      <TableCell>
        <div className="flex justify-end gap-1">
          <Button size="icon-sm" aria-label={`Save changes to #${expense.id}`} onClick={save} disabled={saving}>
            <Check />
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            aria-label={`Cancel editing #${expense.id}`}
            onClick={onCancel}
            disabled={saving}
          >
            <X />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}

interface EditFieldCellsProps extends Pick<ExpenseDraftState, "draft" | "setField"> {
  // Names a control for screen readers: of("Date") -> "Date of #14".
  of: (field: string) => string
}

// The editable cells, in the table's column order: date, merchant, category, amount, paid with, note. None has a
// visible label, so each is named by `of`. Merchant takes the focus, because you just pressed Edit on this row.
function EditFieldCells({ draft, setField, of }: EditFieldCellsProps) {
  return (
    <>
      <TableCell>
        <Input
          type="date"
          aria-label={of("Date")}
          className="h-8 w-36"
          value={draft.spent_on}
          onChange={(e) => setField("spent_on", e.target.value)}
        />
      </TableCell>
      <TableCell>
        <Input
          aria-label={of("Merchant")}
          className="h-8 min-w-32"
          value={draft.merchant}
          onChange={(e) => setField("merchant", e.target.value)}
          // oxlint-disable-next-line jsx-a11y/no-autofocus -- you pressed Edit on this row: the cursor goes to it
          autoFocus
        />
      </TableCell>
      <TableCell>
        <CategorySelect
          ariaLabel={of("Category")}
          className="h-8 w-36"
          value={draft.category_id}
          onChange={(value) => setField("category_id", value)}
        />
      </TableCell>
      <TableCell>
        <Input
          aria-label={of("Amount")}
          className="ml-auto h-8 w-24 text-right"
          inputMode="decimal"
          value={draft.amount}
          onChange={(e) => setField("amount", e.target.value)}
        />
      </TableCell>
      <TableCell>
        <PaymentMethodSelect
          ariaLabel={of("Payment method")}
          className="h-8 w-32"
          value={draft.payment_method}
          onChange={(value) => setField("payment_method", value)}
        />
      </TableCell>
      <TableCell>
        <Input
          aria-label={of("Note")}
          className="h-8 min-w-32"
          value={draft.note}
          onChange={(e) => setField("note", e.target.value)}
        />
      </TableCell>
    </>
  )
}
