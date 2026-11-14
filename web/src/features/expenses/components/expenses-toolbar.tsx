// A part of the expenses feature's table: the line above it, with the count ("140 expenses · showing the newest
// 100 · 2 selected") and "Delete selected" while any row is ticked. Used by expenses-table.tsx.

import { Trash2 } from "lucide-react"

import { plural } from "@/shared/lib/format"
import { Button } from "@/shared/ui/button"

interface ExpensesToolbarProps {
  /** How many expenses match the filters. */
  total: number
  /** How many of them are loaded into the table (the API sends at most a page). */
  shown: number
  /** How many rows are ticked. */
  selected: number
  /** A delete is running: "Delete selected" waits, so the same rows can't be sent twice. */
  deleting: boolean
  /** "Delete selected" was pressed: the table asks the page to confirm the ticked rows. */
  onDeleteSelected: () => void
}

/**
 * The count line above the expenses table. It says how many match, adds "showing the newest N" when the table
 * holds fewer than that, and "N selected" while rows are ticked; "Delete selected" shows only then.
 */
export function ExpensesToolbar({ total, shown, selected, deleting, onDeleteSelected }: ExpensesToolbarProps) {
  return (
    <div className="flex min-h-8 items-center justify-between gap-2 text-sm text-muted-foreground">
      <span>
        {plural(total, "expense")}
        {total > shown && ` · showing the newest ${shown}`}
        {selected > 0 && ` · ${selected} selected`}
      </span>
      {selected > 0 && (
        <Button size="sm" variant="destructive" disabled={deleting} onClick={onDeleteSelected}>
          <Trash2 /> Delete selected
        </Button>
      )}
    </div>
  )
}
