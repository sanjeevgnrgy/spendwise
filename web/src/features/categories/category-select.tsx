// A component of the categories feature: the category dropdown (shadcn's Select), filled from the categories
// query. Public (index.ts): the expenses feature uses it in its Add dialog, edit row and filters.

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

import { useCategories } from "./queries"

/**
 * The value of the "any category" option (see `anyLabel`). <Select> can't use "" as an option's value, so "any
 * category" needs a value of its own; the filters bar turns it back into "no category filter".
 */
export const ANY_CATEGORY = "all"

interface CategorySelectProps {
  /** The category id as text ("" = nothing chosen yet), because <Select> works with strings. */
  value: string
  /** Called with the chosen option's value: a category id as text, or ANY_CATEGORY. */
  onChange: (value: string) => void
  /** Ties it to a visible <Label htmlFor>. */
  id?: string
  className?: string
  /** For a dropdown with no visible <Label>. */
  ariaLabel?: string
  /** Adds a first option meaning "any category" (value ANY_CATEGORY), e.g. "All categories". */
  anyLabel?: string
}

/**
 * The category dropdown, wherever a category is picked: the Add dialog, the inline edit row, the filters. It lists
 * the categories by name. While they load it says "Loading…"; if they can't be loaded it says so and is disabled.
 */
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
