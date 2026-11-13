// Every call to the SpendWise backend goes through this file, so the rest of the app never
// deals with URLs, JSON or HTTP status codes directly.

import type { A2uiAction } from "@/lib/a2ui"

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
  limit?: number // at most this many, newest first
}

// Totals are computed by the backend; the browser only receives the results.
export interface CategoryTotal {
  category_id: number
  category_name: string
  expense_count: number
  total_minor: number
  total: string
}

export interface MonthlySummary {
  month: string // "YYYY-MM"
  currency: string
  expense_count: number
  total_minor: number
  total: string
  by_category: CategoryTotal[] // biggest first
}

export interface MonthTotal {
  month: string // "YYYY-MM"
  expense_count: number
  total_minor: number
  total: string
}

export interface MonthlyTrend {
  currency: string
  months: MonthTotal[] // oldest first, with 0 for months without spending
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

export function getMonthlySummary(month: string): Promise<MonthlySummary> {
  return request<MonthlySummary>(`/summary?month=${month}`)
}

export function getMonthlyTrend(months = 6): Promise<MonthlyTrend> {
  return request<MonthlyTrend>(`/summary/trend?months=${months}`)
}

// ---------- the assistant: AG-UI events streamed from POST /agent ----------

// What starts a run: something typed, or a form's Save (an A2UI `action`, see lib/a2ui.ts).
export type AgentPrompt = { text: string } | { action: A2uiAction }

// The agent's shared state (AG-UI): sent with every run, sent back in STATE_SNAPSHOT events.
export interface AgentState {
  dataVersion: number // goes up each time a tool changed expenses
}

// The AG-UI events the backend sends. Only the fields we use are listed.
export type AgentEvent =
  | { type: "RUN_STARTED"; threadId: string; runId: string }
  | { type: "TEXT_MESSAGE_START"; messageId: string; role: "assistant" }
  | { type: "TEXT_MESSAGE_CONTENT"; messageId: string; delta: string }
  | { type: "TEXT_MESSAGE_END"; messageId: string }
  | { type: "TOOL_CALL_START"; toolCallId: string; toolCallName: string }
  | { type: "TOOL_CALL_ARGS"; toolCallId: string; delta: string } // a piece of the arguments' JSON
  | { type: "TOOL_CALL_END"; toolCallId: string } // the arguments are complete; the tool runs next
  | { type: "TOOL_CALL_RESULT"; toolCallId: string; content: string; metadata?: { ok?: boolean } }
  | { type: "STATE_SNAPSHOT"; snapshot: AgentState }
  | { type: "CUSTOM"; name: string; value: unknown } // name "a2ui": value is one A2UI message, checked in lib/a2ui.ts
  | { type: "RUN_FINISHED"; threadId: string; runId: string }
  | { type: "RUN_ERROR"; message: string; code?: string }

// A random id of 32 hex characters, the length the backend allows for a thread id.
export function newId(): string {
  return crypto.randomUUID().replaceAll("-", "")
}

/**
 * Runs the assistant on one message, calling `onEvent` for each event as soon as it arrives.
 * Resolves on RUN_FINISHED. Throws on RUN_ERROR, or if the connection ends before the run does.
 */
export async function runAgent(
  threadId: string,
  prompt: AgentPrompt,
  state: AgentState,
  onEvent: (event: AgentEvent) => void,
) {
  // AG-UI's run input. The browser names the thread; the server only needs the newest message,
  // because it keeps the conversation's history itself. `state` is the shared state, as we know it.
  const input = {
    threadId,
    runId: newId(),
    state,
    messages: "text" in prompt ? [{ id: newId(), role: "user", content: prompt.text }] : [],
    // A form's Save is an A2UI action message. AG-UI has no official place for one, so it goes in
    // forwardedProps, AG-UI's field for extra data from the client (decisions D124).
    forwardedProps: "action" in prompt ? { a2uiAction: { version: "1.0", action: prompt.action } } : undefined,
  }
  let response: Response
  try {
    // fetch, not EventSource: EventSource can only send GET requests, and a run needs a POST body.
    response = await fetch(`${API_URL}/agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(input),
    })
  } catch {
    throw new ApiError(`Can't reach the SpendWise API at ${API_URL}. Is the backend running?`, 0)
  }
  // Problems found before the stream starts (like a malformed body) are ordinary HTTP errors.
  if (!response.ok || !response.body) throw new ApiError(await errorMessage(response), response.status)

  // Read the body piece by piece as it arrives, instead of waiting for all of it like response.json().
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ""
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value
      // Each SSE event ends with a blank line. A piece can end mid-event, so keep the unfinished tail.
      const blocks = buffer.split("\n\n")
      buffer = blocks.pop() ?? ""
      for (const block of blocks) {
        // Keep the `data:` lines. FastAPI's ": ping" keep-alive comments have none and are skipped.
        const data = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n")
        if (!data) continue
        const event = JSON.parse(data) as AgentEvent
        if (event.type === "RUN_ERROR") throw new Error(event.message)
        onEvent(event)
        if (event.type === "RUN_FINISHED") return
      }
    }
  } finally {
    // Stop reading and close the connection, however we got here (nothing to do if it already ended).
    reader.cancel().catch(() => {})
  }
  throw new Error("The connection closed before the reply was finished.")
}
