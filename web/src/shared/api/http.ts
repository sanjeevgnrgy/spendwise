// The one HTTP client for the SpendWise API. Its types are generated from the backend's OpenAPI
// document (schema.gen.ts), so a request or response that doesn't match the API is a compile error.

import createClient from "openapi-fetch"

import { API_PREFIX } from "@/shared/api/contracts.gen"
import type { components, paths } from "@/shared/api/schema.gen"
import { APP_NAME } from "@/shared/config/app"
import { API_ORIGIN } from "@/shared/config/env"
import { isAbort } from "@/shared/lib/errors"
import { isObject } from "@/shared/lib/guards"

// The API's data shapes, by their backend names: Schemas["ExpenseRead"], Schemas["CategoryRead"]...
export type Schemas = components["schemas"]

export const api = createClient<paths>({ baseUrl: API_ORIGIN })
export const API_URL = `${API_ORIGIN}${API_PREFIX}`

export const UNREACHABLE = `Can't reach the ${APP_NAME} API at ${API_ORIGIN}. Is the backend running?`
export const UNREADABLE = "The API sent an answer this app couldn't read."

export class ApiError extends Error {
  readonly status: number
  readonly problemType?: string

  constructor(message: string, status: number, problemType?: string) {
    super(message)
    this.status = status
    this.problemType = problemType
  }

  // Every backend error is an RFC 9457 problem: {"type", "title", "status", "detail", ...}.
  static fromProblem(body: unknown, status: number): ApiError {
    if (isObject(body) && typeof body.detail === "string") {
      return new ApiError(body.detail, status, typeof body.type === "string" ? body.type : undefined)
    }
    return new ApiError(`Request failed (${status})`, status)
  }
}

// What an openapi-fetch call resolves to: the data (on success) or the problem (on error).
interface Outcome<T> {
  data?: T
  error?: unknown
  response: Response
}

// Await an openapi-fetch call; throw an ApiError with the problem's message if it failed.
async function settle<T>(pending: Promise<Outcome<T>>): Promise<Outcome<T>> {
  let outcome: Outcome<T>
  try {
    outcome = await pending
  } catch (error) {
    // Cancelled on purpose: let the caller (TanStack Query, the Stop button) see that as it is.
    if (isAbort(error)) throw error
    // fetch throws a TypeError when there's no response at all: the backend is down, or CORS blocked it.
    // Anything else (a body that isn't valid JSON) means the backend answered, but unreadably.
    throw new ApiError(error instanceof TypeError ? UNREACHABLE : UNREADABLE, 0)
  }
  if (!outcome.response.ok) throw ApiError.fromProblem(outcome.error, outcome.response.status)
  return outcome
}

// A call that answers with data.
export async function unwrap<T>(pending: Promise<Outcome<T>>): Promise<T> {
  const { data, response } = await settle(pending)
  if (data === undefined) throw new ApiError(`The API sent an empty answer (${response.status})`, response.status)
  return data
}

// A call that answers with nothing (204 No Content), like a delete.
export async function unwrapEmpty(pending: Promise<Outcome<unknown>>): Promise<void> {
  await settle(pending)
}
