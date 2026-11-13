import { useQuery } from "@tanstack/react-query"
import { useCallback, useMemo } from "react"

import { UNKNOWN_CATEGORY } from "@/shared/api/contracts.gen"

import { listCategories } from "./api"

// TanStack Query keys: what a cached answer is filed under. Anything that changes categories
// invalidates `all`, and every list of them reloads.
export const categoryKeys = {
  all: ["categories"] as const,
}

export function useCategories() {
  return useQuery({
    queryKey: categoryKeys.all,
    // `signal` cancels the request if nothing needs the answer any more (e.g. the page was left).
    queryFn: ({ signal }) => listCategories(signal),
  })
}

// id -> name: what every list of expenses needs. While the names are still loading it gives "" (not
// "Unknown", which would be wrong for a moment); "Unknown" only for an id that really isn't there.
export function useCategoryName(): (categoryId: number) => string {
  const { data } = useCategories()
  const names = useMemo(() => (data ? new Map(data.map((category) => [category.id, category.name])) : null), [data])
  return useCallback((categoryId: number) => (names ? (names.get(categoryId) ?? UNKNOWN_CATEGORY) : ""), [names])
}
