// The expenses feature's form model: an expense being typed in (the Add dialog, the inline edit row), and how
// it becomes a request. One place for the trimming and comparing, so both forms send exactly the same kind of data.
// In it: the draft's type, an empty draft, a draft from an expense, "is it filled in?", the POST body, and the
// PATCH body (only what changed). Used by add-expense-dialog.tsx and edit-row.tsx; use-expense-draft.ts holds a
// draft in React state for both.

import type { Expense, ExpenseChanges, NewExpense, PaymentMethod } from "./api"
import { DEFAULT_PAYMENT_METHOD } from "./payment-methods"

/**
 * Everything as text, the way inputs hold it ("" = not filled in yet). The category id is text too, because
 * the dropdown works with strings; the payment method always holds one of the list's values.
 */
export interface ExpenseDraft {
  amount: string
  merchant: string
  category_id: string
  spent_on: string
  payment_method: PaymentMethod
  note: string
}

/** A blank draft for the Add dialog: dated `today` ("YYYY-MM-DD"), with the default payment method. */
export function emptyDraft(today: string): ExpenseDraft {
  return { amount: "", merchant: "", category_id: "", spent_on: today, payment_method: DEFAULT_PAYMENT_METHOD, note: "" }
}

/** An existing expense as a draft, for the edit row: the category id becomes text, and no note becomes "". */
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

/**
 * True when amount, merchant, category and date are filled in (the note is optional). Only "is it filled in?"
 * here. The real rules (amount > 0, at most 2 decimals...) are checked by the backend, so they're written once
 * and apply to every way in (REST, chat, MCP).
 */
export function isComplete(draft: ExpenseDraft): boolean {
  return draft.amount.trim() !== "" && draft.merchant.trim() !== "" && draft.category_id !== "" && draft.spent_on !== ""
}

/** The draft as a POST body: text trimmed, the category id as a number, and an empty note sent as null. */
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

/**
 * Only what actually changed: PATCH is a partial update, so nothing else is overwritten. `expense` is what the
 * draft started from (the edit row passes its own snapshot). An emptied note becomes null, which clears it.
 * An empty object means nothing changed.
 */
export function changesBetween(expense: Expense, draft: ExpenseDraft): ExpenseChanges {
  // Trimmed and converted exactly as for a new expense, so "Subway " and "Subway" count as the same.
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
