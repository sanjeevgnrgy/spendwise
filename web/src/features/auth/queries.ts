// The auth feature's server state, through TanStack Query: the cache keys and a hook per request. Used by the session
// check, the user menu and the sign-in page; `authKeys` is also public (index.ts), so the app's query client can ask
// again who is signed in when any call answers 401.

import { useQuery } from "@tanstack/react-query"

import { getLoginOptions, getSignedInUser } from "./api"

// How long the answer to "who is signed in?" is trusted: after that, it's asked again when the window regains focus
// or the gate is drawn again. Any call that finds the session gone (a 401) asks again at once
// (app/_shell/query-client.ts).
const USER_FRESH_MS = 5 * 60 * 1000

// The root of every auth key, so marking it out of date reaches them all.
const ROOT = ["auth"] as const

/** TanStack Query keys for the auth feature, all filed under ["auth", ...]. */
export const authKeys = {
  all: ROOT,
  user: [...ROOT, "user"] as const,
  options: [...ROOT, "options"] as const,
}

/** Who is signed in: `data` is the user, null when nobody is, undefined while it's being asked. */
export function useSignedInUser() {
  return useQuery({
    queryKey: authKeys.user,
    queryFn: ({ signal }) => getSignedInUser(signal),
    staleTime: USER_FRESH_MS,
  })
}

/** The sign-in page's buttons. They only change with the server's settings, so they're asked once per page load. */
export function useLoginOptions() {
  return useQuery({
    queryKey: authKeys.options,
    queryFn: ({ signal }) => getLoginOptions(signal),
    staleTime: Number.POSITIVE_INFINITY,
  })
}
