import { Search, X } from "lucide-react"

import type { Category, ExpenseFilters } from "@/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

// <Select> can't use "" as an option value, so "all categories" needs its own value.
const ALL = "all"

interface FiltersBarProps {
  categories: Category[]
  filters: ExpenseFilters
  onChange: (filters: ExpenseFilters) => void
}

// The filters live in the page (the parent); this component only shows them and reports changes.
// The page then asks the backend again, which does the actual filtering.
export function FiltersBar({ categories, filters, onChange }: FiltersBarProps) {
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
            onChange={(event) => set({ search: event.target.value || undefined })}
          />
        </div>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="filter-category">Category</Label>
        <Select
          value={filters.category_id ? String(filters.category_id) : ALL}
          onValueChange={(value) => set({ category_id: value === ALL ? undefined : Number(value) })}
        >
          <SelectTrigger id="filter-category" className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All categories</SelectItem>
            {categories.map((category) => (
              <SelectItem key={category.id} value={String(category.id)}>
                {category.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="filter-from">From</Label>
        <Input
          id="filter-from"
          type="date"
          className="w-40"
          value={filters.start_date ?? ""}
          // max/min stop picking a range that ends before it starts (the API would reject it).
          max={filters.end_date}
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
          min={filters.start_date}
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
