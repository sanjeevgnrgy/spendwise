import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

import { useCategories } from "./queries"

// <Select> can't use "" as an option's value, so "any category" needs a value of its own.
export const ANY_CATEGORY = "all"

interface CategorySelectProps {
  value: string // the category id as text ("" = nothing chosen yet), because <Select> works with strings
  onChange: (value: string) => void
  id?: string
  className?: string
  ariaLabel?: string // for a dropdown with no visible <Label>
  anyLabel?: string // adds a first option meaning "any category" (value ANY_CATEGORY), e.g. "All categories"
}

// The category dropdown, wherever a category is picked: the Add dialog, the inline edit row, the filters.
export function CategorySelect({ value, onChange, id, className, ariaLabel, anyLabel }: CategorySelectProps) {
  const { data: categories = [], isPending, isError } = useCategories()
  // Say why the list is empty, instead of an empty dropdown that can't be filled in.
  const placeholder = isError ? "Couldn't load categories" : isPending ? "Loading…" : "Choose a category"

  return (
    <Select value={value} onValueChange={onChange} disabled={isError}>
      <SelectTrigger id={id} className={className} aria-label={ariaLabel}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {anyLabel && <SelectItem value={ANY_CATEGORY}>{anyLabel}</SelectItem>}
        {categories.map((category) => (
          <SelectItem key={category.id} value={String(category.id)}>
            {category.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
