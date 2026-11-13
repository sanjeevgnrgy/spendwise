import { MutationCache, QueryClient } from "@tanstack/react-query"

import { dashboardKeys } from "@/features/dashboard"
import { expenseKeys } from "@/features/expenses"
import { ApiError } from "@/shared/api/http"
import { DATA_SCOPES } from "@/shared/config/data-scopes"

// Client errors (4xx) won't succeed by asking again; a dropped connection or a 5xx might.
const MAX_RETRIES = 1

function isClientError(error: unknown): boolean {
  return error instanceof ApiError && error.status >= 400 && error.status < 500
}

// THE rule for "expenses changed", in one place: every expense list and the Dashboard's totals are
// marked out of date, and whatever is on screen reloads by itself. Used by expense mutations (below)
// and by the assistant (providers.tsx).
export function refreshExpenseData(client: QueryClient): void {
  for (const queryKey of [expenseKeys.all, dashboardKeys.all]) client.invalidateQueries({ queryKey })
}

// The app's one cache of server data. Pages ask it for data instead of fetching by hand; it
// de-duplicates requests, cancels outdated ones, and reloads whatever is marked out of date.
export const queryClient: QueryClient = new QueryClient({
  // A mutation says what kind of data it changed (`meta.changes`); this decides what that makes stale.
  // onSettled, not onSuccess: a delete of several expenses can partly succeed and still report an error.
  mutationCache: new MutationCache({
    onSettled: (_data, _error, _variables, _context, mutation) => {
      if (mutation.meta?.changes === DATA_SCOPES.expenses) refreshExpenseData(queryClient)
    },
  }),
  defaultOptions: {
    queries: {
      retry: (failures, error) => failures < MAX_RETRIES && !isClientError(error),
    },
  },
})
