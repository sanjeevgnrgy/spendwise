// An expense being typed in (the Add dialog, the inline edit row), and how it becomes a request.
// One place for the trimming and comparing, so both forms send exactly the same kind of data.

import type { Expense, ExpenseChanges, NewExpense, PaymentMethod } from "./api"
import { DEFAULT_PAYMENT_METHOD } from "./payment-methods"

// Everything as text, the way inputs hold it ("" = not filled in yet).
export interface ExpenseDraft {
  amount: string
  merchant: string
  category_id: string
  spent_on: string
  payment_method: PaymentMethod
  note: string
}

export function emptyDraft(today: string): ExpenseDraft {
  return { amount: "", merchant: "", category_id: "", spent_on: today, payment_method: DEFAULT_PAYMENT_METHOD, note: "" }
}

export function draftOf(expense: Expense): ExpenseDraft {
  return {
    amount: expense.amount,
    merchant: expense.merchant,
    category_id: String(expense.category_id),
    spent_on: expense.spent_on,
    payment_method: expense.payment_method,
    note: expense.note ?? "",
  }
}

// Only "is it filled in?" here. The real rules (amount > 0, at most 2 decimals...) are checked by the
// backend, so they're written once and apply to every way in (REST, chat, MCP).
export function isComplete(draft: ExpenseDraft): boolean {
  return draft.amount.trim() !== "" && draft.merchant.trim() !== "" && draft.category_id !== "" && draft.spent_on !== ""
}

export function toNewExpense(draft: ExpenseDraft): NewExpense {
  return {
    amount: draft.amount.trim(),
    category_id: Number(draft.category_id),
    merchant: draft.merchant.trim(),
    spent_on: draft.spent_on,
    payment_method: draft.payment_method,
    note: draft.note.trim() || null,
  }
}

// Only what actually changed: PATCH is a partial update, so nothing else is overwritten.
export function changesBetween(expense: Expense, draft: ExpenseDraft): ExpenseChanges {
  const next = toNewExpense(draft)
  const changes: ExpenseChanges = {}
  if (next.spent_on !== expense.spent_on) changes.spent_on = next.spent_on
  if (next.merchant !== expense.merchant) changes.merchant = next.merchant
  if (next.category_id !== expense.category_id) changes.category_id = next.category_id
  if (next.amount !== expense.amount) changes.amount = next.amount
  if (next.payment_method !== expense.payment_method) changes.payment_method = next.payment_method
  if (next.note !== expense.note) changes.note = next.note
  return changes
}
