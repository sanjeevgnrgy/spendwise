// Shared helper: one status for a page that loads several queries together (the Dashboard loads four). It answers
// "did any fail, and with what?", "is any loading?" and "ask again, but only what failed". Part of shared/, so it
// knows no feature; it only reads TanStack Query's result type. Used by the Dashboard page.

import type { UseQueryResult } from "@tanstack/react-query"

/** The parts of a TanStack Query result this helper reads. Any useQuery result fits. */
export type QueryLike = Pick<UseQueryResult, "isError" | "isFetching" | "error" | "refetch">

/** What several queries add up to, for one error card or "couldn't refresh" notice. */
export interface QueryGroupStatus {
  /** The first query (in the order given) whose last request failed; undefined while none has. */
  failed?: QueryLike
  /** Whether any of them is loading right now (a first load, a reload, or a retry). */
  retrying: boolean
  /** Asks again only the queries that failed; the others keep what they have. */
  retry: () => void
}

/**
 * The status of a group of queries shown together. A page shows `failed.error` once (not one card per query),
 * disables its Try again button while `retrying`, and calls `retry` from it. Pure: it only reads the results.
 */
export function queryGroupStatus(queries: readonly QueryLike[]): QueryGroupStatus {
  return {
    failed: queries.find((query) => query.isError),
    retrying: queries.some((query) => query.isFetching),
    // Asking again what already worked would only add load (and flicker) for nothing.
    retry: () => queries.filter((query) => query.isError).forEach((query) => query.refetch()),
  }
}
