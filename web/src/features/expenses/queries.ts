// The expenses feature's server state, through TanStack Query: the cache keys, the list hook, the mutations
// (add, edit, delete) and "is a delete running?". Components use these hooks rather than api.ts, so loading,
// caching, cancelling and reloading are handled in one way. Used by the Expenses page, its table, its edit hook
// and its dialogs; `expenseKeys` and `useExpenses` are also public (index.ts): the app's refresh rule and the
// Dashboard use them.

import { keepPreviousData, useIsMutating, useMutation, useMutationState, useQuery } from "@tanstack/react-query"

import { DATA_SCOPES } from "@/shared/config/data-scopes"
import { isObject } from "@/shared/lib/guards"

import {
  createExpense,
  deleteExpense,
  listExpenses,
  updateExpense,
  type ExpenseChanges,
  type ExpenseFilters,
} from "./api"

// The root every expenses key starts with. Written once, so the query keys and the delete mutation's key can't
// drift apart.
const EXPENSES_ROOT = ["expenses"] as const

/**
 * TanStack Query keys: every expense list is filed under ["expenses", ...]. Marking `all` out of date
 * (app/_shell/query-client.ts does) reloads every list on screen, whatever its filters.
 */
export const expenseKeys = {
  all: EXPENSES_ROOT,
  // One key per set of filters, so each filtered list is cached on its own.
  list: (filters: ExpenseFilters) => [...expenseKeys.all, "list", filters] as const,
  // The delete mutation's key, so the table can tell one is running (useIsDeletingExpenses).
  deleting: [...EXPENSES_ROOT, "delete"] as const,
  // The update mutation's key, so the table can tell which rows are saving (useSavingExpenseIds).
  updating: [...EXPENSES_ROOT, "update"] as const,
}

// Every mutation here says it changed expenses (`meta.changes`). What that makes out of date (these
// lists, the Dashboard's totals...) is decided once, by the app (app/_shell/query-client.ts), not here.
const CHANGES_EXPENSES = { changes: DATA_SCOPES.expenses }

/**
 * The expenses matching `filters` (newest first, with the total), cached per set of filters. Returns
 * TanStack Query's result (`data`, `isPending`, `isError`, `refetch`...). It reloads by itself whenever a
 * change marks expenses out of date: this page's own, or the assistant's.
 */
export function useExpenses(filters: ExpenseFilters) {
  return useQuery({
    queryKey: expenseKeys.list(filters),
    // `signal` cancels a request nobody needs any more, e.g. when the filters change again first.
    queryFn: ({ signal }) => listExpenses(filters, signal),
    // While new filters load, keep showing the previous rows instead of an empty table.
    placeholderData: keepPreviousData,
  })
}

/** Adds an expense: `mutate(newExpense)`. It declares that it changed expenses, so the app reloads what shows them. */
export function useCreateExpense() {
  return useMutation({ mutationFn: createExpense, meta: CHANGES_EXPENSES })
}

/** One edit: which expense, and only the fields that changed. */
export interface ExpenseUpdate {
  id: number
  changes: ExpenseChanges
}

/** Edits one expense: `mutateAsync({ id, changes })`. It declares that it changed expenses. */
export function useUpdateExpense() {
  return useMutation({
    mutationKey: expenseKeys.updating,
    mutationFn: ({ id, changes }: ExpenseUpdate) => updateExpense(id, changes),
    meta: CHANGES_EXPENSES,
  })
}

// The expense id an update mutation was called with, read defensively: the mutation cache types variables as
// unknown, since it holds every kind of mutation.
function updatedIdOf(variables: unknown): number | undefined {
  return isObject(variables) && typeof variables.id === "number" ? variables.id : undefined
}

/**
 * The ids of the expenses being saved right now. Several rows can save at once (save one, open and save another
 * before the first answers), so each running update counts, not only the latest one.
 */
export function useSavingExpenseIds(): number[] {
  const ids = useMutationState({
    filters: { mutationKey: expenseKeys.updating, status: "pending" },
    select: (mutation) => updatedIdOf(mutation.state.variables),
  })
  return ids.filter((id): id is number => id !== undefined)
}

/** What a delete of several expenses did: how many were deleted, and one error for each that wasn't. */
export interface DeleteOutcome {
  deleted: number
  failures: unknown[]
}

/**
 * Deletes several expenses at once: `mutate(ids)`. It doesn't fail when some deletes do: it resolves with a
 * DeleteOutcome, so the caller can say "2 deleted" and "couldn't delete 1" together. It runs under
 * `expenseKeys.deleting`, so the table can tell a delete is running (useIsDeletingExpenses) and disable its
 * delete buttons meanwhile.
 */
export function useDeleteExpenses() {
  return useMutation({
    mutationKey: expenseKeys.deleting,
    // allSettled (not all): one failure shouldn't hide whether the others were deleted. The deletes are sent
    // all at once, not one after another.
    mutationFn: async (ids: number[]): Promise<DeleteOutcome> => {
      const results = await Promise.allSettled(ids.map((id) => deleteExpense(id)))
      const failures = results.flatMap((result) => (result.status === "rejected" ? [result.reason] : []))
      return { deleted: ids.length - failures.length, failures }
    },
    meta: CHANGES_EXPENSES,
  })
}

/**
 * True while any delete started by useDeleteExpenses is running, wherever it was started (the confirmation
 * dialog starts it, the table reads this). Used to disable every delete button, so the same rows can't be sent
 * for deleting twice.
 */
export function useIsDeletingExpenses(): boolean {
  return useIsMutating({ mutationKey: expenseKeys.deleting }) > 0
}
