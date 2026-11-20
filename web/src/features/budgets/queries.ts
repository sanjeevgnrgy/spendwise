// The budgets feature's server state, through TanStack Query: the cache keys, the status hook and the two mutations
// (set a limit, remove one). Components use these hooks rather than api.ts. `budgetKeys` and `useBudgetStatus` are
// also public (index.ts): the app's refresh rule marks budgets out of date when expenses change, and the Dashboard's
// budget card reads the status.

import { useMutation, useQuery } from "@tanstack/react-query"

import { DATA_SCOPES } from "@/shared/config/data-scopes"

import { getBudgetStatus, removeBudget, setBudget, type BudgetScope } from "./api"

/**
 * TanStack Query keys, all filed under ["budgets", ...]. Marking `all` out of date (app/_shell/query-client.ts does,
 * after a budget or an expense changes) reloads every month's status.
 */
export const budgetKeys = {
  all: ["budgets"] as const,
  // One key per month, so each is cached on its own.
  status: (month: string) => [...budgetKeys.all, "status", month] as const,
}

// Both mutations say they changed budgets; what that makes out of date is decided by the app, not here.
const CHANGES_BUDGETS = { changes: DATA_SCOPES.budgets }

/** The status of `month` ("YYYY-MM"), cached per month. Returns TanStack Query's result (`data`, `isError`...). */
export function useBudgetStatus(month: string) {
  return useQuery({ queryKey: budgetKeys.status(month), queryFn: ({ signal }) => getBudgetStatus(month, signal) })
}

/** One limit to set: which budget, and the new limit as typed. */
export interface BudgetUpdate {
  scope: BudgetScope
  limit: string
}

/** Sets a budget's limit: `mutate({ scope, limit })`. It declares that it changed budgets. */
export function useSetBudget() {
  return useMutation({ mutationFn: ({ scope, limit }: BudgetUpdate) => setBudget(scope, limit), meta: CHANGES_BUDGETS })
}

/** Removes a budget: `mutate(scope)`. It declares that it changed budgets. */
export function useRemoveBudget() {
  return useMutation({ mutationFn: removeBudget, meta: CHANGES_BUDGETS })
}
