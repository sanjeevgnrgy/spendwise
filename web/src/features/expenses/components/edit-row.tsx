import { Check, X } from "lucide-react"
import { useState, type KeyboardEvent } from "react"

import { CategorySelect } from "@/features/categories"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { TableCell, TableRow } from "@/shared/ui/table"

import type { Expense, ExpenseChanges } from "../api"
import { changesBetween, draftOf, type ExpenseDraft } from "../expense-form"
import { PaymentMethodSelect } from "./payment-method-select"

interface EditRowProps {
  expense: Expense
  saving: boolean // this row's save is in flight
  onSave: (changes: ExpenseChanges) => void
  onCancel: () => void
}

// One table row in "edit mode". It must render the same columns, in the same order, as the
// normal row in expenses-table.tsx: select, id, date, merchant, category, amount, paid with, note, actions.
export function EditRow({ expense: current, saving, onSave, onCancel }: EditRowProps) {
  // The expense as it was when editing started. If the list reloads meanwhile (say the assistant changed
  // this expense), Save still compares the draft with what you started from, so it only sends the fields
  // YOU changed, and never quietly undoes someone else's change.
  const [expense] = useState(current)
  // A private draft of the values while editing. The table's data only changes after Save succeeds,
  // so Cancel can simply throw the draft away.
  const [draft, setDraft] = useState<ExpenseDraft>(() => draftOf(current))
  // Every control says which expense it edits, for screen readers ("Merchant of #14").
  const of = (field: string) => `${field} of #${expense.id}`

  function set<K extends keyof ExpenseDraft>(field: K, value: ExpenseDraft[K]) {
    setDraft((previous) => ({ ...previous, [field]: value }))
  }

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

  return (
    <TableRow className="bg-muted/50" onKeyDown={handleKeyDown}>
      <TableCell />
      {/* The id can't be edited: it's how the expense is found. */}
      <TableCell className="text-muted-foreground tabular-nums">#{expense.id}</TableCell>
      <TableCell>
        <Input
          type="date"
          aria-label={of("Date")}
          className="h-8 w-36"
          value={draft.spent_on}
          onChange={(e) => set("spent_on", e.target.value)}
        />
      </TableCell>
      <TableCell>
        <Input
          aria-label={of("Merchant")}
          className="h-8 min-w-32"
          value={draft.merchant}
          onChange={(e) => set("merchant", e.target.value)}
          // oxlint-disable-next-line jsx-a11y/no-autofocus -- you pressed Edit on this row: the cursor goes to it
          autoFocus
        />
      </TableCell>
      <TableCell>
        <CategorySelect
          ariaLabel={of("Category")}
          className="h-8 w-36"
          value={draft.category_id}
          onChange={(value) => set("category_id", value)}
        />
      </TableCell>
      <TableCell>
        <Input
          aria-label={of("Amount")}
          className="ml-auto h-8 w-24 text-right"
          inputMode="decimal"
          value={draft.amount}
          onChange={(e) => set("amount", e.target.value)}
        />
      </TableCell>
      <TableCell>
        <PaymentMethodSelect ariaLabel={of("Payment method")} className="h-8 w-32" value={draft.payment_method} onChange={(value) => set("payment_method", value)} />
      </TableCell>
      <TableCell>
        <Input aria-label={of("Note")} className="h-8 min-w-32" value={draft.note} onChange={(e) => set("note", e.target.value)} />
      </TableCell>
      <TableCell>
        <div className="flex justify-end gap-1">
          <Button size="icon-sm" aria-label={`Save changes to #${expense.id}`} onClick={save} disabled={saving}>
            <Check />
          </Button>
          <Button size="icon-sm" variant="ghost" aria-label={`Cancel editing #${expense.id}`} onClick={onCancel} disabled={saving}>
            <X />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}
