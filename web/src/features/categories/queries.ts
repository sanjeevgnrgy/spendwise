// The categories feature's server state, through TanStack Query: the cache key, the list hook, and a name lookup.
// Used by CategorySelect; public (index.ts): the expenses table and the Dashboard use the list and the names.

import { useQuery } from "@tanstack/react-query"
import { useCallback, useMemo } from "react"

import { listCategories } from "./api"
import { useTexts } from "./i18n"

/**
 * TanStack Query keys: what a cached answer is filed under. Invalidating `all` (as a change to categories would)
 * reloads every list of them.
 */
export const categoryKeys = {
  all: ["categories"] as const,
}

/**
 * Every category, cached under one key and shared by every dropdown and name lookup on screen (one request serves
 * them all). Returns TanStack Query's result (`data`, `isPending`, `isError`...).
 */
export function useCategories() {
  return useQuery({
    queryKey: categoryKeys.all,
    // `signal` cancels the request if nothing needs the answer any more (e.g. the page was left).
    queryFn: ({ signal }) => listCategories(signal),
  })
}

/**
 * id -> name: what every list of expenses needs. While the names are still loading it gives "" (not
 * "Unknown", which would be wrong for a moment); "Unknown" (the categories text "unknown", in the language on now)
 * only for an id that really isn't there. The function stays the same until the categories or the language change,
 * so a table's columns built from it aren't rebuilt. A page that uses it loads the categories texts with its own.
 */
export function useCategoryName(): (categoryId: number) => string {
  const { data } = useCategories()
  const { t } = useTexts()
  // A Map, built once per answer, so each lookup is direct rather than a search through the list.
  const names = useMemo(() => (data ? new Map(data.map((category) => [category.id, category.name])) : null), [data])
  return useCallback((categoryId: number) => (names ? (names.get(categoryId) ?? t("unknown")) : ""), [names, t])
}
