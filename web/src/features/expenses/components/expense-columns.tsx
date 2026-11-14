// A part of the expenses feature's table: what each column shows and how it sorts (TanStack Table v9 column
// definitions), the table's opted-in features, the sortable header and its aria-sort. Pure configuration: no
// state and no hooks, so the table decides when the columns are rebuilt. Used by expenses-table.tsx.

import {
  createColumnHelper,
  createSortedRowModel,
  rowSelectionFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  tableFeatures,
  type Column_RowSorting,
  type SortDirection,
} from "@tanstack/react-table"
import { Pencil, Trash2 } from "lucide-react"

import { formatDate, formatMoney } from "@/shared/lib/format"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Checkbox } from "@/shared/ui/checkbox"

import type { Expense } from "../api"
import { paymentMethodLabel } from "../payment-methods"
import { SortButton } from "./sort-button"

/**
 * The TanStack Table features the expenses table uses. In v9 you opt in to each one: here sorting (with its
 * sorted row model) and row selection. Defined once, outside any component, so it never changes.
 */
export const expenseTableFeatures = tableFeatures({
  rowSortingFeature,
  rowSelectionFeature,
  sortedRowModel: createSortedRowModel(),
})

// Builds the column definitions, typed for these features and for Expense rows.
const columnHelper = createColumnHelper<typeof expenseTableFeatures, Expense>()

// What screen readers announce for a sorted column (the header cell's aria-sort).
const ARIA_SORT = { asc: "ascending", desc: "descending" } as const

/** The header cell's aria-sort for a column's direction; undefined (no attribute) for a column that isn't sorted. */
export function ariaSortOf(sorted: false | SortDirection) {
  return sorted ? ARIA_SORT[sorted] : undefined
}

// The part of a column that a sortable header reads: its direction, and the handler that toggles it.
type SortableColumn = Pick<
  Column_RowSorting<typeof expenseTableFeatures, Expense>,
  "getIsSorted" | "getToggleSortingHandler"
>

/**
 * A column's `header`: a SortButton titled `title`, wired to whichever column it heads. `align: "end"` pushes the
 * button to the right, over a right-aligned column (the amount).
 */
export function sortableHeader(title: string, align?: "end") {
  return ({ column }: { column: SortableColumn }) => {
    const button = <SortButton title={title} sorted={column.getIsSorted()} onClick={column.getToggleSortingHandler()} />
    return align === "end" ? <div className="flex justify-end">{button}</div> : button
  }
}

/** What the columns need from the table around them. */
export interface ExpenseColumnOptions {
  /** A category's name by id (the Category column shows and sorts by it). */
  categoryName: (id: number) => string
  /** A delete is running: every Delete button is disabled meanwhile. */
  deleting: boolean
  /** Edit was pressed on this expense's row. */
  onEdit: (id: number) => void
  /** Delete was pressed on a row: asks the page to confirm and delete it. */
  onDelete: (expenses: Expense[]) => void
}

// Tick boxes. The header's ticks every row, and shows a dash when only some are ticked.
function selectColumn() {
  return columnHelper.display({
    id: "select",
    header: ({ table }) => (
      <Checkbox
        aria-label="Select all"
        checked={table.getIsAllRowsSelected() || (table.getIsSomeRowsSelected() && "indeterminate")}
        onCheckedChange={(value) => table.toggleAllRowsSelected(value === true)}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        aria-label={`Select #${row.original.id}`}
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(value === true)}
      />
    ),
    enableSorting: false,
  })
}

// The expense's own fields, in display order. Sorting happens in the browser, within the rows already loaded.
function dataColumns(categoryName: ExpenseColumnOptions["categoryName"]) {
  return columnHelper.columns([
    // The id as "#14": the assistant shows ids the same way, so you can say "delete #14".
    columnHelper.accessor("id", {
      header: sortableHeader("ID"),
      cell: ({ getValue }) => <span className="text-muted-foreground tabular-nums">#{getValue()}</span>,
      sortFn: sortFn_basic,
    }),
    columnHelper.accessor("spent_on", {
      header: sortableHeader("Date"),
      cell: ({ getValue }) => formatDate(getValue()),
      // "YYYY-MM-DD" strings sort correctly as plain text.
      sortFn: sortFn_alphanumeric,
    }),
    columnHelper.accessor("merchant", {
      header: sortableHeader("Merchant"),
      cell: ({ getValue }) => <span className="font-medium">{getValue()}</span>,
      sortFn: sortFn_alphanumeric,
    }),
    // Shows (and sorts by) the category's name, not its id.
    columnHelper.accessor((expense) => categoryName(expense.category_id), {
      id: "category",
      header: sortableHeader("Category"),
      sortFn: sortFn_alphanumeric,
    }),
    // Sort by the paise value (a whole number), but display the rupee string.
    columnHelper.accessor("amount_minor", {
      id: "amount",
      header: sortableHeader("Amount", "end"),
      cell: ({ row }) => (
        <div className="text-right tabular-nums">{formatMoney(row.original.amount, row.original.currency)}</div>
      ),
      sortFn: sortFn_basic,
    }),
    columnHelper.accessor("payment_method", {
      header: "Paid with",
      cell: ({ getValue }) => <Badge variant="secondary">{paymentMethodLabel(getValue())}</Badge>,
      enableSorting: false,
    }),
    columnHelper.accessor("note", {
      header: "Note",
      cell: ({ getValue }) => <span className="text-muted-foreground">{getValue() ?? ""}</span>,
      enableSorting: false,
    }),
  ])
}

// Edit opens this row's edit row; Delete asks the page to confirm. Delete is disabled while a delete runs.
function actionsColumn({ deleting, onEdit, onDelete }: ExpenseColumnOptions) {
  return columnHelper.display({
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end gap-1">
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label={`Edit #${row.original.id}`}
          onClick={() => onEdit(row.original.id)}
        >
          <Pencil />
        </Button>
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label={`Delete #${row.original.id}`}
          disabled={deleting}
          onClick={() => onDelete([row.original])}
        >
          <Trash2 className="text-destructive" />
        </Button>
      </div>
    ),
  })
}

/**
 * The expenses table's columns, in order: select, id, date, merchant, category, amount, paid with, note, actions
 * (EditRow draws the same order). ID, Date, Merchant, Category and Amount sort when their header is clicked. Every
 * call builds new definitions, so the table memoises the result and rebuilds it only when an option changes.
 */
export function expenseColumns(options: ExpenseColumnOptions) {
  return columnHelper.columns([selectColumn(), ...dataColumns(options.categoryName), actionsColumn(options)])
}
