// The one HTTP client for the SpendWise API. Its types are generated from the backend's OpenAPI
// document (schema.gen.ts), so a request or response that doesn't match the API is a compile error.
// Part of shared/ (it knows no feature). Every feature's api.ts calls the backend through `api` and `unwrap`;
// ApiError is also read by app/query-client.ts (its retry rule) and the assistant's stream.

import createClient from "openapi-fetch"

import type { components, paths } from "@/shared/api/schema.gen"
import { APP_NAME } from "@/shared/config/app"
import { API_ORIGIN } from "@/shared/config/env"
import { isAbort } from "@/shared/lib/errors"
import { isObject } from "@/shared/lib/guards"

/** The API's data shapes, by their backend names: Schemas["ExpenseRead"], Schemas["CategoryRead"]... */
export type Schemas = components["schemas"]

/**
 * The typed client (openapi-fetch): api.GET("/api/v1/expenses", { params, signal }) and so on. A path, parameter or
 * body the API doesn't accept is a compile error. Wrap each call in unwrap() or unwrapEmpty().
 */
export const api = createClient<paths>({ baseUrl: API_ORIGIN })

/** The message when no answer came back at all: the backend is down, unreachable, or blocked by CORS. */
export const UNREACHABLE = `Can't reach the ${APP_NAME} API at ${API_ORIGIN}. Is the backend running?`
/** The message when the backend answered, but with something that couldn't be read (not valid JSON). */
export const UNREADABLE = "The API sent an answer this app couldn't read."

/**
 * A failed API call. `message` is for people (the backend's own `detail`, or one of the messages above), `status`
 * is the HTTP status (0 when no answer came back), and `problemType` is the problem's `type`, when it had one.
 */
export class ApiError extends Error {
  /** The HTTP status; 0 when the backend couldn't be reached or its answer couldn't be read. */
  readonly status: number
  /** The RFC 9457 problem's `type` (which kind of failure), when the backend sent one. */
  readonly problemType?: string

  constructor(message: string, status: number, problemType?: string) {
    super(message)
    this.status = status
    this.problemType = problemType
  }

  /**
   * An ApiError from an error answer's body. Every backend error is an RFC 9457 problem:
   * {"type", "title", "status", "detail", ...}; its `detail` becomes the message. A body that isn't one gives a
   * plain "Request failed (status)".
   */
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

/**
 * Awaits a call that answers with data, and returns the data. Throws ApiError if the request failed or the answer
 * was empty; an aborted request is re-thrown as it is (so TanStack Query or the Stop button can ignore it).
 */
export async function unwrap<T>(pending: Promise<Outcome<T>>): Promise<T> {
  const { data, response } = await settle(pending)
  if (data === undefined) throw new ApiError(`The API sent an empty answer (${response.status})`, response.status)
  return data
}

/** Awaits a call that answers with nothing (204 No Content), like a delete. Throws like unwrap(). */
export async function unwrapEmpty(pending: Promise<Outcome<unknown>>): Promise<void> {
  await settle(pending)
}
