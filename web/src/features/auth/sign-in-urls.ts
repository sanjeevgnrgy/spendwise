// Where signing in starts and ends, as pure functions: the backend's login route (a navigation, not an API call), the
// sign-in page with the page to come back to, the check on the sign-out link, and the text for a failed sign-in's
// ?error= code. Part of the auth
// feature; used by the session check and the sign-in page. Every name comes from the generated contract (AUTH).

import { AUTH } from "@/shared/api/contracts.gen"
import type { paths } from "@/shared/api/schema.gen"
import { ROUTES } from "@/shared/config/routes"

import type { FailureText } from "./i18n"

// Checked against the API's paths, like every other call (a typo is a compile error).
const LOGIN_PATH = "/api/v1/auth/login" satisfies keyof paths
// The text for an ?error= code this app doesn't know (a newer server's).
const UNKNOWN_FAILURE: FailureText = "unknown"
// The contract's failure keys (cancelled, expired, ...). Object.keys can't type them, but they're the keys of a
// generated constant, not network data, so the cast can't be wrong; each is also a key of en.ts's "failures".
const FAILURE_KEYS = Object.keys(AUTH.failures) as (keyof typeof AUTH.failures)[]

/**
 * The backend's login route: the browser goes there (a full navigation), and on to the provider. `option` (a
 * button's key) skips straight to that way of signing in; `returnTo` is the page to come back to, which the backend
 * checks (only a path in the app is kept).
 */
export function loginUrl(option: string | undefined, returnTo: string | null): string {
  const params = new URLSearchParams()
  if (option) params.set(AUTH.params.option, option)
  if (returnTo) params.set(AUTH.params.returnTo, returnTo)
  const query = params.toString()
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH
}

/** The sign-in page, remembering `returnTo` (the address the person wanted) unless it's the start page. */
export function signInPath(returnTo: string): string {
  if (!returnTo || returnTo === ROUTES.dashboard) return ROUTES.signIn
  return `${ROUTES.signIn}?${new URLSearchParams({ [AUTH.params.returnTo]: returnTo })}`
}

/** The address the browser is at, as a path with its query and fragment: what the sign-in page should return to. */
export function currentPath(location: Pick<Location, "pathname" | "search" | "hash">): string {
  return `${location.pathname}${location.search}${location.hash}`
}

/**
 * `url` as a path on this site (`origin`, the page's own), or null if it leads anywhere else. For links the server
 * sends (the sign-out link in GET /auth/user): network data is never trusted with a navigation, so another host, or a
 * scheme like javascript:, is refused.
 */
export function ownSitePath(url: string, origin: string): string | null {
  try {
    const target = new URL(url, origin)
    return target.origin === origin ? `${target.pathname}${target.search}` : null
  } catch {
    return null
  }
}

/**
 * Where the sign-in page sends someone who is already signed in: the page they were heading for (`returnTo`, from the
 * address), if it's on this site and isn't the sign-in page itself; otherwise the start page. `returnTo` is whatever
 * the address says, so it's never followed as it is: only its path on this site is used.
 */
export function afterSignIn(returnTo: string | null, origin: string): string {
  const path = returnTo ? ownSitePath(returnTo, origin) : null
  return path && !path.startsWith(ROUTES.signIn) ? path : ROUTES.dashboard
}

/**
 * The text explaining a failed sign-in's ?error= code (the contract's AUTH.failures): its key under "failures", the
 * generic one for a code this app doesn't know, or null when there's no code.
 */
export function failureText(code: string | null): FailureText | null {
  if (!code) return null
  return FAILURE_KEYS.find((key) => AUTH.failures[key] === code) ?? UNKNOWN_FAILURE
}
