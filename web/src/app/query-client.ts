// The app's TanStack Query client: the one cache of server data, its retry rule, and THE rule for what reloads
// after a kind of data changes. Part of the app composition (app/): it's the only place that knows both the
// Expenses and the Dashboard features, so a feature only says "I changed expenses" (a mutation's `meta.changes`,
// or the assistant's onDataChanged) and this file decides what that makes out of date.
// Used by providers.tsx (QueryClientProvider, and the assistant's refresh).

import { MutationCache, QueryClient, type QueryKey } from "@tanstack/react-query"

import { dashboardKeys } from "@/features/dashboard"
import { expenseKeys } from "@/features/expenses"
import { ApiError } from "@/shared/api/http"
import { DATA_SCOPES, type DataScope } from "@/shared/config/data-scopes"

// A failed query is asked again once (two tries in all) before its error is shown, and only if asking again
// might help. Client errors (4xx) won't succeed by asking again; a dropped connection or a 5xx might.
const MAX_RETRIES = 1

// A 4xx answer: the backend refused the request itself (invalid, or not found), so repeating it would fail too.
// An unreachable backend is an ApiError with status 0, so it isn't one of these and does get its retry.
function isClientError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 400 && error.status < 500
}

/**
 * THE rule for "this kind of data changed", in one place: for each data scope, the query keys a change to it
 * makes out of date. Every scope must have an entry (a missing one is a compile error), so a new scope can't be
 * forgotten here. Expenses: every expense list, and the Dashboard's totals (which add expenses up).
 * Each key is a prefix: expenseKeys.all matches every expense list, whatever its filters.
 */
export const STALE_AFTER: Readonly<Record<DataScope, readonly QueryKey[]>> = {
  [DATA_SCOPES.expenses]: [expenseKeys.all, dashboardKeys.all],
}

/**
 * Marks out of date everything a change to `scope` affects (STALE_AFTER), so whatever is on screen reloads by
 * itself. Queries a mounted component uses reload now; the others reload when they're next shown. Used by
 * mutations (below, through their `meta.changes`) and by the assistant (providers.tsx).
 */
export function refreshAfter(client: QueryClient, scope: DataScope): void {
  for (const queryKey of STALE_AFTER[scope]) client.invalidateQueries({ queryKey })
}

/**
 * The app's one cache of server data. Pages ask it for data instead of fetching by hand; it
 * de-duplicates requests, cancels outdated ones, and reloads whatever is marked out of date.
 * Options not set here keep TanStack's defaults: for example, data counts as out of date as soon as it arrives, so
 * a query reloads when a page that uses it is shown again or the window regains focus.
 */
export const queryClient: QueryClient = new QueryClient({
  // A mutation says what kind of data it changed (`meta.changes`); refreshAfter decides what that makes stale.
  // onSettled, not onSuccess: refresh after a failure too, because a request can fail after the backend already
  // made the change (the answer was lost on the way back), and reloading shows what's really stored.
  // (Deleting several expenses doesn't rely on this: that mutation succeeds even when some deletes fail.)
  mutationCache: new MutationCache({
    onSettled: (_data, _error, _variables, _context, mutation) => {
      const scope = mutation.meta?.changes
      if (scope) refreshAfter(queryClient, scope)
    },
  }),
  defaultOptions: {
    // Only queries retry. Mutations keep TanStack's default of no retries: asking twice to save an expense
    // could save it twice.
    queries: {
      // `failures` is how many tries had failed before this one: 0 when the first try fails, so exactly one retry.
      retry: (failures, error) => failures < MAX_RETRIES && !isClientError(error),
    },
  },
})
