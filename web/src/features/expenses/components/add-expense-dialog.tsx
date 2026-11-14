// A component of the expenses feature: the "Add expense" button and the dialog it opens, a form for the amount,
// date, merchant, category, payment method and note. Used by the Expenses page, next to its title.

import { Plus } from "lucide-react"
import { useState, type FormEvent } from "react"
import { toast } from "sonner"

import { CategorySelect } from "@/features/categories"
import { DEFAULT_CURRENCY } from "@/shared/api/contracts.gen"
import { messageOf } from "@/shared/lib/errors"
import { todayIso } from "@/shared/lib/format"
import { Button } from "@/shared/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"

import { emptyDraft, isComplete, toNewExpense } from "../expense-form"
import { useCreateExpense } from "../queries"
import { useExpenseDraft, type ExpenseDraftState } from "../use-expense-draft"
import { LabeledField } from "./labeled-field"
import { PaymentMethodSelect } from "./payment-method-select"

// A blank draft dated today. A function, so "today" is worked out each time the form starts again, not once.
const blankDraft = () => emptyDraft(todayIso())

/**
 * The Add expense button and its dialog. Save is enabled once the required fields are filled in (the backend
 * checks the rest). On success the dialog closes, a toast says so, and the form starts empty again; on failure
 * the backend's reason shows as a toast and the dialog stays open with what you typed. Cancel keeps the draft
 * for next time. The list reloads by itself, because the mutation declares that it changed expenses.
 */
export function AddExpenseDialog() {
  // Whether the dialog is open; the draft lives in useExpenseDraft, so closing the dialog keeps it.
  const [open, setOpen] = useState(false)
  const { draft, setField, reset } = useExpenseDraft(blankDraft)
  const create = useCreateExpense()

  // Save (the button, or Enter in a text box): send the draft as a new expense.
  function handleSubmit(event: FormEvent) {
    event.preventDefault() // stop the browser's default form submit, which would reload the page
    create.mutate(toNewExpense(draft), {
      onSuccess: () => {
        toast.success("Expense added")
        setOpen(false)
        reset()
      },
      // e.g. "Amount must be greater than 0", straight from the backend's rules. The dialog stays open.
      onError: (error) => toast.error(messageOf(error)),
    })
  }

  // Save shows "Saving…" and waits while the request runs; Cancel only closes the dialog (the draft stays).
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus /> Add expense
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Add expense</DialogTitle>
            <DialogDescription>Amounts are in {DEFAULT_CURRENCY}, e.g. 450.50.</DialogDescription>
          </DialogHeader>

          <AddExpenseFields draft={draft} setField={setField} />

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={!isComplete(draft) || create.isPending}>
              {create.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// The form's fields, between its header and its buttons. Amount and date share a row, as do category and payment
// method; each control's id ties it to its label.
function AddExpenseFields({ draft, setField }: Pick<ExpenseDraftState, "draft" | "setField">) {
  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        <LabeledField id="add-amount" label="Amount">
          <Input
            id="add-amount"
            inputMode="decimal"
            placeholder="450.50"
            value={draft.amount}
            onChange={(event) => setField("amount", event.target.value)}
          />
        </LabeledField>
        <LabeledField id="add-date" label="Date">
          <Input
            id="add-date"
            type="date"
            value={draft.spent_on}
            onChange={(event) => setField("spent_on", event.target.value)}
          />
        </LabeledField>
      </div>

      <LabeledField id="add-merchant" label="Merchant">
        <Input
          id="add-merchant"
          placeholder="Swiggy"
          value={draft.merchant}
          onChange={(event) => setField("merchant", event.target.value)}
        />
      </LabeledField>

      <div className="grid grid-cols-2 gap-3">
        <LabeledField id="add-category" label="Category">
          <CategorySelect id="add-category" value={draft.category_id} onChange={(value) => setField("category_id", value)} />
        </LabeledField>
        <LabeledField id="add-payment" label="Paid with">
          <PaymentMethodSelect
            id="add-payment"
            value={draft.payment_method}
            onChange={(value) => setField("payment_method", value)}
          />
        </LabeledField>
      </div>

      <LabeledField id="add-note" label="Note (optional)">
        <Input
          id="add-note"
          placeholder="Dinner"
          value={draft.note}
          onChange={(event) => setField("note", event.target.value)}
        />
      </LabeledField>
    </>
  )
}
