// A component of the expenses feature: the filters above the expenses table (search, category, a date range,
// and Clear filters). Used by the Expenses page, which owns the filters and sends them with its query. Its texts
// come from the feature's i18n namespace.

import { Search, X } from "lucide-react"

import { ANY_CATEGORY, CategorySelect } from "@/features/categories"
import { LabeledField } from "@/shared/components/labeled-field"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"

import type { ExpenseFilters } from "../../api"
import { useTexts } from "../../i18n"

interface FiltersBarProps {
  /** The filters as they are now (the page's state). */
  filters: ExpenseFilters
  /** Called with the whole new set of filters after any change. */
  onChange: (filters: ExpenseFilters) => void
}

/**
 * The filters live in the page (the parent); this component only shows them and reports changes.
 * The page then asks the backend again, which does the actual filtering.
 *
 * Draws Search (merchant or note), Category ("All categories" removes that filter), From and To, and a
 * Clear filters button while any filter is set. A field that's emptied is removed from the filters
 * (undefined), never sent as "".
 */
export function FiltersBar({ filters, onChange }: FiltersBarProps) {
  const { t } = useTexts()
  // Change one filter, keep the others.
  const set = (changes: Partial<ExpenseFilters>) => onChange({ ...filters, ...changes })
  // Is any filter set? Then "Clear filters" shows.
  const hasFilters = Object.values(filters).some((value) => value !== undefined && value !== "")

  // An empty search is left out entirely: the backend refuses search="". From's max and To's min stop picking a
  // range that ends before it starts (the API would reject it).
  return (
    <div className="flex flex-wrap items-end gap-3">
      <LabeledField id="filter-search" label={t("filters.search")}>
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="filter-search"
            placeholder={t("filters.searchPlaceholder")}
            className="w-56 pl-8"
            value={filters.search ?? ""}
            onChange={(event) => set({ search: event.target.value || undefined })}
          />
        </div>
      </LabeledField>

      <LabeledField id="filter-category" label={t("fields.category")}>
        <CategorySelect
          id="filter-category"
          className="w-44"
          anyLabel={t("filters.allCategories")}
          value={filters.category_id ? String(filters.category_id) : ANY_CATEGORY}
          onChange={(value) => set({ category_id: value === ANY_CATEGORY ? undefined : Number(value) })}
        />
      </LabeledField>

      <LabeledField id="filter-from" label={t("filters.from")}>
        <Input
          id="filter-from"
          type="date"
          className="w-40"
          value={filters.start_date ?? ""}
          max={filters.end_date ?? undefined}
          onChange={(event) => set({ start_date: event.target.value || undefined })}
        />
      </LabeledField>

      <LabeledField id="filter-to" label={t("filters.to")}>
        <Input
          id="filter-to"
          type="date"
          className="w-40"
          value={filters.end_date ?? ""}
          min={filters.start_date ?? undefined}
          onChange={(event) => set({ end_date: event.target.value || undefined })}
        />
      </LabeledField>

      {hasFilters && (
        <Button variant="ghost" onClick={() => onChange({})}>
          <X /> {t("filters.clear")}
        </Button>
      )}
    </div>
  )
}
