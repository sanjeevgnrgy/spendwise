import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query"

import { DATA_SCOPES } from "@/shared/config/data-scopes"

import { createExpense, deleteExpense, listExpenses, updateExpense, type ExpenseChanges, type ExpenseFilters } from "./api"

// TanStack Query keys: every expense list is filed under ["expenses", ...].
export const expenseKeys = {
  all: ["expenses"] as const,
  list: (filters: ExpenseFilters) => [...expenseKeys.all, "list", filters] as const,
  deleting: ["expenses", "delete"] as const, // the delete mutation, so the table can tell one is running
}

// Every mutation here says it changed expenses (`meta.changes`). What that makes out of date (these
// lists, the Dashboard's totals...) is decided once, by the app (app/query-client.ts), not here.
const CHANGES_EXPENSES = { changes: DATA_SCOPES.expenses }

export function useExpenses(filters: ExpenseFilters) {
  return useQuery({
    queryKey: expenseKeys.list(filters),
    // `signal` cancels a request nobody needs any more, e.g. when the filters change again first.
    queryFn: ({ signal }) => listExpenses(filters, signal),
    // While new filters load, keep showing the previous rows instead of an empty table.
    placeholderData: keepPreviousData,
  })
}

export function useCreateExpense() {
  return useMutation({ mutationFn: createExpense, meta: CHANGES_EXPENSES })
}

export function useUpdateExpense() {
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: ExpenseChanges }) => updateExpense(id, changes),
    meta: CHANGES_EXPENSES,
  })
}

export interface DeleteOutcome {
  deleted: number
  failures: unknown[]
}

export function useDeleteExpenses() {
  return useMutation({
    mutationKey: expenseKeys.deleting,
    // allSettled (not all): one failure shouldn't hide whether the others were deleted.
    mutationFn: async (ids: number[]): Promise<DeleteOutcome> => {
      const results = await Promise.allSettled(ids.map((id) => deleteExpense(id)))
      const failures = results.flatMap((result) => (result.status === "rejected" ? [result.reason] : []))
      return { deleted: ids.length - failures.length, failures }
    },
    meta: CHANGES_EXPENSES,
  })
}
