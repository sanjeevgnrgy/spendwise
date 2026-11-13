import { Check, X } from "lucide-react"
import { useState, type KeyboardEvent } from "react"

import type { Category, Expense, ExpenseChanges, PaymentMethod } from "@/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { TableCell, TableRow } from "@/components/ui/table"
import { CategorySelect, PaymentMethodSelect } from "@/pages/expenses/selects"

interface EditRowProps {
  expense: Expense
  categories: Category[]
  onSave: (changes: ExpenseChanges) => Promise<void>
  onCancel: () => void
}

// One table row in "edit mode". It must render the same columns, in the same order, as the
// normal row in expenses-table.tsx: select, id, date, merchant, category, amount, paid with, note, actions.
export function EditRow({ expense: current, categories, onSave, onCancel }: EditRowProps) {
  // The expense as it was when editing started. If the list reloads meanwhile (say the assistant changed
  // this expense), Save still compares the draft with what you started from, so it only sends the fields
  // YOU changed, and never quietly undoes someone else's change.
  const [expense] = useState(current)
  // A private draft of the values while editing. The table's data only changes after Save succeeds,
  // so Cancel can simply throw the draft away.
  const [draft, setDraft] = useState({
    spent_on: expense.spent_on,
    merchant: expense.merchant,
    category_id: String(expense.category_id),
    amount: expense.amount,
    payment_method: expense.payment_method as PaymentMethod,
    note: expense.note ?? "",
  })
  const [saving, setSaving] = useState(false)

  function set<K extends keyof typeof draft>(field: K, value: (typeof draft)[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  async function save() {
    // Enter can fire again (or repeat while held) before the first save finishes: send it once.
    if (saving) return
    // Send only what actually changed: PATCH is a partial update.
    const changes: ExpenseChanges = {}
    if (draft.spent_on !== expense.spent_on) changes.spent_on = draft.spent_on
    if (draft.merchant.trim() !== expense.merchant) changes.merchant = draft.merchant.trim()
    if (Number(draft.category_id) !== expense.category_id) changes.category_id = Number(draft.category_id)
    if (draft.amount.trim() !== expense.amount) changes.amount = draft.amount.trim()
    if (draft.payment_method !== expense.payment_method) changes.payment_method = draft.payment_method
    const note = draft.note.trim() || null
    if (note !== expense.note) changes.note = note

    setSaving(true)
    await onSave(changes)
    setSaving(false)
  }

  // Enter saves and Escape cancels, but only while typing in a text box (dropdowns use those keys themselves).
  function handleKeyDown(event: KeyboardEvent) {
    if (!(event.target instanceof HTMLInputElement)) return
    if (event.key === "Enter") save()
    if (event.key === "Escape") onCancel()
  }

  return (
    <TableRow className="bg-muted/50" onKeyDown={handleKeyDown}>
      <TableCell />
      {/* The id can't be edited: it's how the expense is found. */}
      <TableCell className="text-muted-foreground tabular-nums">#{expense.id}</TableCell>
      <TableCell>
        <Input type="date" className="h-8 w-36" value={draft.spent_on} onChange={(e) => set("spent_on", e.target.value)} />
      </TableCell>
      <TableCell>
        <Input className="h-8 min-w-32" value={draft.merchant} onChange={(e) => set("merchant", e.target.value)} autoFocus />
      </TableCell>
      <TableCell>
        <CategorySelect
          className="h-8 w-36"
          categories={categories}
          value={draft.category_id}
          onChange={(value) => set("category_id", value)}
        />
      </TableCell>
      <TableCell>
        <Input
          className="ml-auto h-8 w-24 text-right"
          inputMode="decimal"
          value={draft.amount}
          onChange={(e) => set("amount", e.target.value)}
        />
      </TableCell>
      <TableCell>
        <PaymentMethodSelect className="h-8 w-32" value={draft.payment_method} onChange={(value) => set("payment_method", value)} />
      </TableCell>
      <TableCell>
        <Input className="h-8 min-w-32" value={draft.note} onChange={(e) => set("note", e.target.value)} />
      </TableCell>
      <TableCell>
        <div className="flex justify-end gap-1">
          <Button size="icon-sm" aria-label="Save changes" onClick={save} disabled={saving}>
            <Check />
          </Button>
          <Button size="icon-sm" variant="ghost" aria-label="Cancel editing" onClick={onCancel} disabled={saving}>
            <X />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  )
}
