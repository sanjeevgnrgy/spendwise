// The auth feature's API calls and their types: who is signed in, and the sign-in page's buttons. The only file in
// this feature that calls the backend; the session itself is a cookie the browser sends by itself (D186), so nothing
// here ever sees a token. Used by queries.ts.

import { api, ApiError, unwrap, type Schemas } from "@/shared/api/http"

/** Who is signed in, and the link that signs this browser out. */
export type SignedInUser = Schemas["SignedInUser"]
/** One of the sign-in page's buttons: what it sends back as ?option=, and what it says. */
export type LoginOption = Schemas["LoginOptionRead"]

// The status the API answers when there's no live session (the backend's AuthenticationError).
const SIGNED_OUT = 401

/** Whether `error` says the session has ended (or never was): a 401 from any API call. */
export function isSignedOut(error: unknown): boolean {
  return error instanceof ApiError && error.status === SIGNED_OUT
}

/**
 * Who is signed in; null when nobody is (the API's 401), which isn't an error here: it's the answer the session check
 * acts on. Throws ApiError for anything else (the backend unreachable, a 5xx).
 */
export async function getSignedInUser(signal?: AbortSignal): Promise<SignedInUser | null> {
  try {
    return await unwrap(api.GET("/api/v1/auth/user", { signal }))
  } catch (error) {
    if (isSignedOut(error)) return null
    throw error
  }
}

/** The sign-in page's buttons ([] means: offer the provider's own page). Throws ApiError if it fails. */
export function getLoginOptions(signal?: AbortSignal): Promise<LoginOption[]> {
  return unwrap(api.GET("/api/v1/auth/options", { signal }))
}
