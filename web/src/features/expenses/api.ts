// The expenses feature's API calls and their types: the only file in this feature that talks to the backend.
// Every type comes from the generated contract (schema.gen.ts), never written by hand, and every call goes
// through the shared typed client (`api`), so a wrong path, parameter or body is a compile error.
// A failed call throws an ApiError carrying the backend's own message (see shared/api/http.ts).
// Used by queries.ts, which wraps each call in a TanStack Query hook; the rest of the feature uses the types.

import type { paths } from "@/shared/api/schema.gen"
import { api, unwrap, unwrapEmpty, type Schemas } from "@/shared/api/http"

/**
 * One stored expense as the API sends it. `amount` is the money as text ("450.50"), for display;
 * `amount_minor` is the same amount in paise, a whole number (exact, and what the table sorts by).
 */
export type Expense = Schemas["ExpenseRead"]
/** A save's answer (POST, PATCH): the expense as stored, and what the server noticed about the save (D212). */
export type SavedExpense = Schemas["SavedExpense"]
/** GET /expenses's answer: up to `limit` expenses, newest first (`items`), and how many match in all (`total`). */
export type ExpenseList = Schemas["ExpenseList"]
/** The body of POST /expenses. The backend checks the real rules (amount > 0, a known category...). */
export type NewExpense = Schemas["NewExpense"]
/** The body of PATCH /expenses/{id}: only the fields to change. Only `note` may be null, which clears it. */
export type ExpenseChanges = Schemas["ExpenseChanges"]
/** How an expense was paid: "cash", "upi", "card"... (the backend's list, generated). */
export type PaymentMethod = Schemas["PaymentMethod"]
/** GET /expenses's query parameters, straight from the API's description. Every one is optional. */
export type ExpenseFilters = NonNullable<paths["/api/v1/expenses"]["get"]["parameters"]["query"]>

// One expense's address: PATCH and DELETE fill in {expense_id}.
const EXPENSE = "/api/v1/expenses/{expense_id}"

/**
 * The expenses matching `filters`, newest first. `signal` lets TanStack Query cancel a request nobody needs
 * any more. Throws ApiError if the request fails (an aborted request is re-thrown as it is).
 */
export function listExpenses(filters: ExpenseFilters, signal?: AbortSignal): Promise<ExpenseList> {
  return unwrap(api.GET("/api/v1/expenses", { params: { query: filters }, signal }))
}

/**
 * Saves a new expense and returns it as stored (with its id) and the save's notices. Throws ApiError with the backend's
 * reason.
 */
export function createExpense(expense: NewExpense): Promise<SavedExpense> {
  return unwrap(api.POST("/api/v1/expenses", { body: expense }))
}

/**
 * Changes only the fields in `changes` and returns the updated expense and the save's notices. Throws ApiError with
 * the backend's reason (an invalid value, or an expense that no longer exists).
 */
export function updateExpense(id: number, changes: ExpenseChanges): Promise<SavedExpense> {
  return unwrap(api.PATCH(EXPENSE, { params: { path: { expense_id: id } }, body: changes }))
}

/** Deletes one expense. The API answers 204 with no body, so this resolves to nothing; throws ApiError if it fails. */
export function deleteExpense(id: number): Promise<void> {
  return unwrapEmpty(api.DELETE(EXPENSE, { params: { path: { expense_id: id } } }))
}
