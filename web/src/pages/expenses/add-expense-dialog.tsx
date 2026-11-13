import { Plus } from "lucide-react"
import { useState, type FormEvent } from "react"

import type { Category, NewExpense, PaymentMethod } from "@/api"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { todayIso } from "@/lib/format"
import { CategorySelect, PaymentMethodSelect } from "@/pages/expenses/selects"

interface AddExpenseDialogProps {
  categories: Category[]
  // Returns true if the expense was saved, so the dialog knows whether to close.
  onAdd: (expense: NewExpense) => Promise<boolean>
}

interface FormValues {
  amount: string
  merchant: string
  category_id: string
  spent_on: string
  payment_method: PaymentMethod
  note: string
}

function emptyForm(): FormValues {
  return { amount: "", merchant: "", category_id: "", spent_on: todayIso(), payment_method: "upi", note: "" }
}

export function AddExpenseDialog({ categories, onAdd }: AddExpenseDialogProps) {
  // Each piece of state is a value React remembers between renders; changing it re-renders the dialog.
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<FormValues>(emptyForm)
  const [saving, setSaving] = useState(false)

  // Change one field, keep the others. A new object (not a mutation) is what tells React to re-render.
  function setField<K extends keyof FormValues>(field: K, value: FormValues[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault() // stop the browser's default form submit, which would reload the page
    setSaving(true)
    const saved = await onAdd({
      amount: form.amount.trim(),
      category_id: Number(form.category_id),
      merchant: form.merchant.trim(),
      spent_on: form.spent_on,
      payment_method: form.payment_method,
      note: form.note.trim() || null,
    })
    setSaving(false)
    if (saved) {
      setOpen(false)
      setForm(emptyForm())
    }
    // If it failed, the dialog stays open with the values, and the page shows the error as a toast.
  }

  // Only "is it filled in?" here. The real rules (amount > 0, at most 2 decimals...) are checked by
  // the backend, so they're written once and apply to every way in (REST, chat, MCP).
  const canSave = form.amount.trim() !== "" && form.merchant.trim() !== "" && form.category_id !== "" && form.spent_on !== ""

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
            <DialogDescription>Amounts are in rupees, e.g. 450.50.</DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="add-amount">Amount</Label>
              <Input
                id="add-amount"
                inputMode="decimal"
                placeholder="450.50"
                value={form.amount}
                onChange={(event) => setField("amount", event.target.value)}
                autoFocus
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="add-date">Date</Label>
              <Input
                id="add-date"
                type="date"
                value={form.spent_on}
                onChange={(event) => setField("spent_on", event.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="add-merchant">Merchant</Label>
            <Input
              id="add-merchant"
              placeholder="Swiggy"
              value={form.merchant}
              onChange={(event) => setField("merchant", event.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="add-category">Category</Label>
              <CategorySelect
                id="add-category"
                categories={categories}
                value={form.category_id}
                onChange={(value) => setField("category_id", value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="add-payment">Paid with</Label>
              <PaymentMethodSelect
                id="add-payment"
                value={form.payment_method}
                onChange={(value) => setField("payment_method", value)}
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="add-note">Note (optional)</Label>
            <Input
              id="add-note"
              placeholder="Dinner"
              value={form.note}
              onChange={(event) => setField("note", event.target.value)}
            />
          </div>

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={!canSave || saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
