import { Search, X } from "lucide-react"

import { ANY_CATEGORY, CategorySelect } from "@/features/categories"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"

import type { ExpenseFilters } from "../api"

interface FiltersBarProps {
  filters: ExpenseFilters
  onChange: (filters: ExpenseFilters) => void
}

// The filters live in the page (the parent); this component only shows them and reports changes.
// The page then asks the backend again, which does the actual filtering.
export function FiltersBar({ filters, onChange }: FiltersBarProps) {
  // Change one filter, keep the others.
  const set = (changes: Partial<ExpenseFilters>) => onChange({ ...filters, ...changes })
  const hasFilters = Object.values(filters).some((value) => value !== undefined && value !== "")

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="grid gap-1.5">
        <Label htmlFor="filter-search">Search</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="filter-search"
            placeholder="Merchant or note"
            className="w-56 pl-8"
            value={filters.search ?? ""}
            // An empty search is left out entirely: the backend refuses search="".
            onChange={(event) => set({ search: event.target.value || undefined })}
          />
        </div>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="filter-category">Category</Label>
        <CategorySelect
          id="filter-category"
          className="w-44"
          anyLabel="All categories"
          value={filters.category_id ? String(filters.category_id) : ANY_CATEGORY}
          onChange={(value) => set({ category_id: value === ANY_CATEGORY ? undefined : Number(value) })}
        />
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="filter-from">From</Label>
        <Input
          id="filter-from"
          type="date"
          className="w-40"
          value={filters.start_date ?? ""}
          // max/min stop picking a range that ends before it starts (the API would reject it).
          max={filters.end_date ?? undefined}
          onChange={(event) => set({ start_date: event.target.value || undefined })}
        />
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="filter-to">To</Label>
        <Input
          id="filter-to"
          type="date"
          className="w-40"
          value={filters.end_date ?? ""}
          min={filters.start_date ?? undefined}
          onChange={(event) => set({ end_date: event.target.value || undefined })}
        />
      </div>

      {hasFilters && (
        <Button variant="ghost" onClick={() => onChange({})}>
          <X /> Clear filters
        </Button>
      )}
    </div>
  )
}
