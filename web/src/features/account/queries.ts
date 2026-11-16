// The account feature's server state, through TanStack Query: the cache keys, a hook per list, and the mutations
// (sign a browser out, sign every other out, make a token, revoke one). Components use these hooks rather than api.ts.
// Used by the Settings page's cards; `accountKeys` is also public (index.ts), for the app's refresh rule.

import { useMutation, useQuery } from "@tanstack/react-query"

import { DATA_SCOPES } from "@/shared/config/data-scopes"

import {
  createAccessToken,
  listAccessTokens,
  listSessions,
  revokeAccessToken,
  signOutOtherSessions,
  signOutSession,
} from "./api"

// The root of every account key, so marking it out of date reaches them all.
const ROOT = ["account"] as const

/** TanStack Query keys for the account feature, all filed under ["account", ...]. */
export const accountKeys = {
  all: ROOT,
  sessions: [...ROOT, "sessions"] as const,
  tokens: [...ROOT, "tokens"] as const,
}

// What each mutation declares it changed; the app's refresh rule (app/_shell/query-client.ts) reloads the list.
const CHANGES_SESSIONS = { changes: DATA_SCOPES.sessions } as const
const CHANGES_TOKENS = { changes: DATA_SCOPES.accessTokens } as const

/** The person's live sessions (the browsers they're signed in on). */
export function useSessions() {
  return useQuery({ queryKey: accountKeys.sessions, queryFn: ({ signal }) => listSessions(signal) })
}

/** The person's access tokens. */
export function useAccessTokens() {
  return useQuery({ queryKey: accountKeys.tokens, queryFn: ({ signal }) => listAccessTokens(signal) })
}

/** Signs one other browser out: `mutate(sessionId)`. */
export function useSignOutSession() {
  return useMutation({ mutationFn: signOutSession, meta: CHANGES_SESSIONS })
}

/** Signs every other browser out: `mutate()`. */
export function useSignOutOtherSessions() {
  return useMutation({ mutationFn: signOutOtherSessions, meta: CHANGES_SESSIONS })
}

/**
 * Makes a token: `mutate({ name, lifetime_days })`; its answer holds the token, the only time it's sent. gcTime 0: the
 * answer isn't kept in the mutation cache once the dialog that shows it is gone, so the token doesn't linger in memory.
 */
export function useCreateAccessToken() {
  return useMutation({ mutationFn: createAccessToken, meta: CHANGES_TOKENS, gcTime: 0 })
}

/** Revokes a token: `mutate(tokenId)`. */
export function useRevokeAccessToken() {
  return useMutation({ mutationFn: revokeAccessToken, meta: CHANGES_TOKENS })
}
