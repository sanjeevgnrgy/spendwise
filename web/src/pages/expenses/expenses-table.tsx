import {
  createColumnHelper,
  createSortedRowModel,
  flexRender,
  rowSelectionFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  tableFeatures,
  useTable,
  type SortDirection,
} from "@tanstack/react-table"
import { ArrowDown, ArrowUp, ArrowUpDown, Pencil, Trash2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import type { Category, Expense, ExpenseChanges } from "@/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatDate, formatMoney, paymentMethodLabel } from "@/lib/format"
import { EditRow } from "@/pages/expenses/edit-row"

// TanStack Table v9: you opt in to each feature you use. Here: sorting (with its sorted row
// model) and row selection. Defined once, outside the component, so it never changes.
const features = tableFeatures({
  rowSortingFeature,
  rowSelectionFeature,
  sortedRowModel: createSortedRowModel(),
})
const columnHelper = createColumnHelper<typeof features, Expense>()

interface SortButtonProps {
  title: string
  sorted: false | SortDirection
  onClick?: (event: unknown) => void
}

// A column header you can click to sort; the arrow shows the current direction.
function SortButton({ title, sorted, onClick }: SortButtonProps) {
  const Icon = sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ArrowUpDown
  return (
    <Button variant="ghost" size="sm" className="-mx-2.5" onClick={onClick}>
      {title}
      <Icon className="size-3.5" />
    </Button>
  )
}

interface ExpensesTableProps {
  expenses: Expense[]
  categories: Category[]
  loading: boolean
  onSave: (id: number, changes: ExpenseChanges) => Promise<boolean>
  // Asks the page to confirm and delete these expenses (one row, or all selected rows).
  onDelete: (expenses: Expense[]) => void
}

export function ExpensesTable({ expenses, categories, loading, onSave, onDelete }: ExpensesTableProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const categoryNames = useMemo(() => new Map(categories.map((c) => [c.id, c.name])), [categories])

  // The column definitions: what each column shows, and how it sorts. useMemo keeps the same
  // array between renders (rebuilding it only when categories change), as TanStack recommends.
  const columns = useMemo(
    () =>
      columnHelper.columns([
        columnHelper.display({
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
              aria-label="Select row"
              checked={row.getIsSelected()}
              onCheckedChange={(value) => row.toggleSelected(value === true)}
            />
          ),
          enableSorting: false,
        }),
        columnHelper.accessor("spent_on", {
          header: ({ column }) => (
            <SortButton title="Date" sorted={column.getIsSorted()} onClick={column.getToggleSortingHandler()} />
          ),
          cell: ({ getValue }) => formatDate(getValue()),
          // "YYYY-MM-DD" strings sort correctly as plain text.
          sortFn: sortFn_alphanumeric,
        }),
        columnHelper.accessor("merchant", {
          header: ({ column }) => (
            <SortButton title="Merchant" sorted={column.getIsSorted()} onClick={column.getToggleSortingHandler()} />
          ),
          cell: ({ getValue }) => <span className="font-medium">{getValue()}</span>,
          sortFn: sortFn_alphanumeric,
        }),
        columnHelper.accessor((expense) => categoryNames.get(expense.category_id) ?? "Unknown", {
          id: "category",
          header: ({ column }) => (
            <SortButton title="Category" sorted={column.getIsSorted()} onClick={column.getToggleSortingHandler()} />
          ),
          sortFn: sortFn_alphanumeric,
        }),
        // Sort by the paise value (a whole number), but display the rupee string.
        columnHelper.accessor("amount_minor", {
          id: "amount",
          header: ({ column }) => (
            <div className="flex justify-end">
              <SortButton title="Amount" sorted={column.getIsSorted()} onClick={column.getToggleSortingHandler()} />
            </div>
          ),
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
        columnHelper.display({
          id: "actions",
          header: () => <span className="sr-only">Actions</span>,
          cell: ({ row }) => (
            <div className="flex justify-end gap-1">
              <Button size="icon-sm" variant="ghost" aria-label="Edit" onClick={() => setEditingId(row.original.id)}>
                <Pencil />
              </Button>
              <Button size="icon-sm" variant="ghost" aria-label="Delete" onClick={() => onDelete([row.original])}>
                <Trash2 className="text-destructive" />
              </Button>
            </div>
          ),
        }),
      ]),
    [categoryNames, onDelete],
  )

  const table = useTable({
    features,
    columns,
    data: expenses,
    // Use the expense id as the row id, so selection and editing follow the expense, not its position.
    getRowId: (expense) => String(expense.id),
    enableRowSelection: true,
  })

  // New data (after a filter change, add, edit or delete) clears the selection, so hidden or
  // already-deleted rows can't stay selected by accident.
  useEffect(() => {
    table.resetRowSelection()
  }, [expenses, table])

  const rows = table.getRowModel().rows
  const selected = table.getSelectedRowModel().rows.map((row) => row.original)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex min-h-8 items-center justify-between gap-2 text-sm text-muted-foreground">
        <span>
          {expenses.length} {expenses.length === 1 ? "expense" : "expenses"}
          {selected.length > 0 && ` · ${selected.length} selected`}
        </span>
        {selected.length > 0 && (
          <Button size="sm" variant="destructive" onClick={() => onDelete(selected)}>
            <Trash2 /> Delete selected
          </Button>
        )}
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  {loading ? "Loading…" : "No expenses match these filters."}
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) =>
                row.original.id === editingId ? (
                  <EditRow
                    key={row.id}
                    expense={row.original}
                    categories={categories}
                    onCancel={() => setEditingId(null)}
                    onSave={async (changes) => {
                      if (await onSave(row.original.id, changes)) setEditingId(null)
                    }}
                  />
                ) : (
                  <TableRow key={row.id} data-state={row.getIsSelected() ? "selected" : undefined}>
                    {/* getAllCells: v9 only has getVisibleCells with the column-visibility feature, which we don't use. */}
                    {row.getAllCells().map((cell) => (
                      <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                    ))}
                  </TableRow>
                ),
              )
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
