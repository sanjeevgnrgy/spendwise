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
import { Label } from "@/shared/ui/label"

import { emptyDraft, isComplete, toNewExpense, type ExpenseDraft } from "../expense-form"
import { useCreateExpense } from "../queries"
import { PaymentMethodSelect } from "./payment-method-select"

export function AddExpenseDialog() {
  // Each piece of state is a value React remembers between renders; changing it re-renders the dialog.
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<ExpenseDraft>(() => emptyDraft(todayIso()))
  const create = useCreateExpense()

  // Change one field, keep the others. A new object (not a mutation) is what tells React to re-render.
  function setField<K extends keyof ExpenseDraft>(field: K, value: ExpenseDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault() // stop the browser's default form submit, which would reload the page
    create.mutate(toNewExpense(draft), {
      onSuccess: () => {
        toast.success("Expense added")
        setOpen(false)
        setDraft(emptyDraft(todayIso()))
      },
      // e.g. "Amount must be greater than 0", straight from the backend's rules. The dialog stays open.
      onError: (error) => toast.error(messageOf(error)),
    })
  }

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

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="add-amount">Amount</Label>
              <Input
                id="add-amount"
                inputMode="decimal"
                placeholder="450.50"
                value={draft.amount}
                onChange={(event) => setField("amount", event.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="add-date">Date</Label>
              <Input
                id="add-date"
                type="date"
                value={draft.spent_on}
                onChange={(event) => setField("spent_on", event.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="add-merchant">Merchant</Label>
            <Input
              id="add-merchant"
              placeholder="Swiggy"
              value={draft.merchant}
              onChange={(event) => setField("merchant", event.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="add-category">Category</Label>
              <CategorySelect id="add-category" value={draft.category_id} onChange={(value) => setField("category_id", value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="add-payment">Paid with</Label>
              <PaymentMethodSelect
                id="add-payment"
                value={draft.payment_method}
                onChange={(value) => setField("payment_method", value)}
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="add-note">Note (optional)</Label>
            <Input
              id="add-note"
              placeholder="Dinner"
              value={draft.note}
              onChange={(event) => setField("note", event.target.value)}
            />
          </div>

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
