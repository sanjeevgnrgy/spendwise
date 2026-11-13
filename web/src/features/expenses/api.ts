import type { paths } from "@/shared/api/schema.gen"
import { api, unwrap, unwrapEmpty, type Schemas } from "@/shared/api/http"

export type Expense = Schemas["ExpenseRead"]
export type ExpenseList = Schemas["ExpenseList"]
export type NewExpense = Schemas["CreateExpense"]
export type ExpenseChanges = Schemas["ExpenseChanges"]
export type PaymentMethod = Schemas["PaymentMethod"]
// GET /expenses's query parameters, straight from the API's description.
export type ExpenseFilters = NonNullable<paths["/api/v1/expenses"]["get"]["parameters"]["query"]>

const EXPENSE = "/api/v1/expenses/{expense_id}"

export function listExpenses(filters: ExpenseFilters, signal?: AbortSignal): Promise<ExpenseList> {
  return unwrap(api.GET("/api/v1/expenses", { params: { query: filters }, signal }))
}

export function createExpense(expense: NewExpense): Promise<Expense> {
  return unwrap(api.POST("/api/v1/expenses", { body: expense }))
}

export function updateExpense(id: number, changes: ExpenseChanges): Promise<Expense> {
  return unwrap(api.PATCH(EXPENSE, { params: { path: { expense_id: id } }, body: changes }))
}

export function deleteExpense(id: number): Promise<void> {
  return unwrapEmpty(api.DELETE(EXPENSE, { params: { path: { expense_id: id } } }))
}
