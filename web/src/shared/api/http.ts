// The one HTTP client for the SpendWise API. Its types are generated from the backend's OpenAPI
// document (schema.gen.ts), so a request or response that doesn't match the API is a compile error.
// Part of shared/ (it knows no feature). Every feature's api.ts calls the backend through `api` and `unwrap`;
// ApiError is also read by app/query-client.ts (its retry rule) and the assistant's stream.

import createClient from "openapi-fetch"

import { AUTH } from "@/shared/api/contracts.gen"
import type { components, paths } from "@/shared/api/schema.gen"
import { APP_NAME } from "@/shared/config/app"
import { i18n, languageHeaders, type CommonTexts } from "@/shared/i18n"
import { isAbort, UserFacingError } from "@/shared/lib/errors"
import { isObject } from "@/shared/lib/guards"

/** The API's data shapes, by their backend names: Schemas["ExpenseRead"], Schemas["CategoryRead"]... */
export type Schemas = components["schemas"]

/**
 * The typed client (openapi-fetch): api.GET("/api/v1/expenses", { params, signal }) and so on. A path, parameter or
 * body the API doesn't accept is a compile error. Wrap each call in unwrap() or unwrapEmpty().
 * No base URL: every call goes to the page's own origin (/api/v1/...), where the dev server or a reverse proxy
 * forwards it to the backend (D184).
 */
export const api = createClient<paths>()

/**
 * The headers every API call carries: the language on now (the server writes its texts, an error's detail, in it),
 * and X-CSRF, which says the app's own page sent it (the server refuses any call without it, D186). Used by `api`
 * and by the assistant's stream, which calls fetch itself.
 */
export function apiHeaders(): Record<string, string> {
  return { ...languageHeaders(), [AUTH.csrfHeader]: AUTH.csrfValue }
}

api.use({
  onRequest({ request }) {
    for (const [name, value] of Object.entries(apiHeaders())) request.headers.set(name, value)
    return request
  },
})

/** One of the client's own error messages: a key of the common "errors" texts. */
type ClientMessage = keyof CommonTexts["errors"]

// What a proxy in front of the backend answers when it can't reach it (Vite's dev server sends 502). The backend's
// own 502s (a service it depends on failed) are always problems, so they're never mistaken for these.
const GATEWAY_FAILURES: ReadonlySet<number> = new Set([502, 503, 504])

/**
 * A failed API call. `message` is for people (the backend's own `detail`, which the server writes for people, or one
 * of the client's own messages), `status` is the HTTP status (0 when no answer came back), and `problemType` is the
 * problem's `type`, when it had one.
 */
export class ApiError extends UserFacingError {
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
   * An ApiError whose message is one of the client's own texts, looked up each time it's read: an error already on
   * screen (TanStack Query keeps it) follows a language switch. (A backend `detail` is the server's text.)
   */
  static ofText(text: ClientMessage, status: number, values: Record<string, string | number> = {}): ApiError {
    const read = () => i18n.t(`errors.${text}`, values)
    // Built with the text as it reads now, so the stack trace (captured here) carries it; then `message` becomes a
    // getter on this one error. (A class accessor can't replace Error's own `message` field.)
    const error = new ApiError(read(), status)
    Object.defineProperty(error, "message", { get: read, configurable: true })
    return error
  }

  /**
   * An ApiError from an error answer's body. Every backend error is an RFC 9457 problem:
   * {"type", "title", "status", "detail", ...}; its `detail` becomes the message. A gateway failure that isn't one
   * came from the proxy in front of the backend, so it's unreachableError(); any other body gives a plain "Request
   * failed (status)".
   */
  static fromProblem(body: unknown, status: number): ApiError {
    if (isObject(body) && typeof body.detail === "string") {
      return new ApiError(body.detail, status, typeof body.type === "string" ? body.type : undefined)
    }
    if (GATEWAY_FAILURES.has(status)) return unreachableError()
    return ApiError.ofText("requestFailed", status, { status })
  }
}

/**
 * The error when no answer came from the backend: the page's server can't be reached, or the proxy in front of the
 * backend answered for it (502/503/504). Its status is 0, "no answer", so queries still retry it. It doesn't name an
 * address (the browser console's failed request, or the dev server's terminal, does, for developers).
 */
export function unreachableError(): ApiError {
  return ApiError.ofText("unreachable", 0, { app: APP_NAME })
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
    // fetch throws a TypeError when there's no response at all: the page's server is down or the network is.
    // Anything else (a body that isn't valid JSON) means the backend answered, but unreadably.
    throw error instanceof TypeError ? unreachableError() : ApiError.ofText("unreadable", 0)
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
  if (data === undefined) throw ApiError.ofText("emptyAnswer", response.status, { status: response.status })
  return data
}

/** Awaits a call that answers with nothing (204 No Content), like a delete. Throws like unwrap(). */
export async function unwrapEmpty(pending: Promise<Outcome<unknown>>): Promise<void> {
  await settle(pending)
}
