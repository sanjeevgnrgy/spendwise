// Every call to the SpendWise backend goes through this file, so the rest of the app never
// deals with URLs, JSON or HTTP status codes directly.

// Where the backend runs. Override it with VITE_API_URL in web/.env if it moves.
const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

// ---------- types: the shapes the backend sends and accepts ----------

export type PaymentMethod = "cash" | "upi" | "card" | "netbanking" | "wallet" | "other"
export const PAYMENT_METHODS: PaymentMethod[] = ["cash", "upi", "card", "netbanking", "wallet", "other"]

export interface Category {
  id: number
  name: string
  icon: string
}

export interface Expense {
  id: number
  amount_minor: number // paise: the exact stored value
  amount: string // rupees for display, e.g. "450.50" (a string, so it never becomes a float)
  currency: string
  category_id: number
  merchant: string
  note: string | null
  spent_on: string // "YYYY-MM-DD"
  payment_method: PaymentMethod
  created_at: string
}

// What POST /expenses accepts: no id or created_at, the server decides those.
export interface NewExpense {
  amount: string
  currency?: string
  category_id: number
  merchant: string
  note?: string | null
  spent_on: string
  payment_method: PaymentMethod
}

// PATCH sends only the fields that change.
export type ExpenseChanges = Partial<NewExpense>

export interface ExpenseFilters {
  start_date?: string
  end_date?: string
  category_id?: number
  search?: string
}

// ---------- errors ----------

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    // Our own errors look like {"detail": "Category 9 does not exist"};
    // FastAPI's validation errors are a list: {"detail": [{"loc": [...], "msg": "..."}]}.
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail.map((e: { loc: unknown[]; msg: string }) => `${e.loc.at(-1)}: ${e.msg}`).join("; ")
    }
  } catch {
    // Not JSON: fall through to a generic message.
  }
  return `Request failed (${response.status})`
}

// ---------- the one function that talks HTTP ----------

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  // Only send a Content-Type when there is a body; plain GETs then need no CORS "preflight" check.
  const headers = init.body ? { "Content-Type": "application/json" } : undefined
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    // fetch only throws when there's no response at all: the backend is down, or CORS blocked it.
    throw new ApiError(`Can't reach the SpendWise API at ${API_URL}. Is the backend running?`, 0)
  }
  if (!response.ok) throw new ApiError(await errorMessage(response), response.status)
  // 204 No Content (after a delete) has no body to read.
  return (response.status === 204 ? undefined : await response.json()) as T
}

function toQuery(filters: ExpenseFilters): string {
  const params = new URLSearchParams()
  // Skip empty filters: the backend rejects unknown or empty parameters (e.g. search="").
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ""
}

// ---------- the API ----------

export function listCategories(): Promise<Category[]> {
  return request<Category[]>("/categories")
}

export function listExpenses(filters: ExpenseFilters = {}): Promise<Expense[]> {
  return request<Expense[]>(`/expenses${toQuery(filters)}`)
}

export function createExpense(expense: NewExpense): Promise<Expense> {
  return request<Expense>("/expenses", { method: "POST", body: JSON.stringify(expense) })
}

export function updateExpense(id: number, changes: ExpenseChanges): Promise<Expense> {
  return request<Expense>(`/expenses/${id}`, { method: "PATCH", body: JSON.stringify(changes) })
}

export function deleteExpense(id: number): Promise<void> {
  return request<void>(`/expenses/${id}`, { method: "DELETE" })
}
