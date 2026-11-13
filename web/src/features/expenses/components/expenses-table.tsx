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
  type RowSelectionState,
  type SortDirection,
} from "@tanstack/react-table"
import { ArrowDown, ArrowUp, ArrowUpDown, Pencil, Trash2 } from "lucide-react"
import { useIsMutating } from "@tanstack/react-query"
import { useMemo, useState } from "react"
import { toast } from "sonner"

import { useCategoryName } from "@/features/categories"
import { messageOf } from "@/shared/lib/errors"
import { formatDate, formatMoney, plural } from "@/shared/lib/format"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Checkbox } from "@/shared/ui/checkbox"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

import type { Expense, ExpenseChanges } from "../api"
import { paymentMethodLabel } from "../payment-methods"
import { expenseKeys, useUpdateExpense } from "../queries"
import { EditRow } from "./edit-row"

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

// What screen readers announce for a sorted column (the header cell's aria-sort).
const ARIA_SORT = { asc: "ascending", desc: "descending" } as const

// A column header you can click to sort; the arrow shows the current direction.
function SortButton({ title, sorted, onClick }: SortButtonProps) {
  const Icon = sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ArrowUpDown
  return (
    <Button variant="ghost" size="sm" className="-mx-2.5" onClick={onClick} aria-label={`Sort by ${title}`}>
      {title}
      <Icon className="size-3.5" />
    </Button>
  )
}

function pickSort(sorted: false | SortDirection) {
  return sorted ? ARIA_SORT[sorted] : undefined
}

interface ExpensesTableProps {
  expenses: Expense[]
  total: number // how many match the filters; `expenses` may hold fewer (the API's limit)
  loading: boolean
  // Asks the page to confirm and delete these expenses (one row, or all selected rows).
  onDelete: (expenses: Expense[]) => void
}

export function ExpensesTable({ expenses, total, loading, onDelete }: ExpensesTableProps) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const update = useUpdateExpense()
  // A delete is running (the confirmation dialog started it): its rows can't be deleted twice meanwhile.
  const deleting = useIsMutating({ mutationKey: expenseKeys.deleting }) > 0
  const categoryName = useCategoryName()
  // Which rows are ticked, as { "12": true, "15": true }. Kept here (not only inside the table)
  // so this component decides when it's cleared.
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [selectionFor, setSelectionFor] = useState(expenses)

  // New data (after a filter change, add, edit or delete) clears the selection, so hidden or
  // already-deleted rows can't stay selected by accident. React's "reset state when a prop changes"
  // pattern: compare during render instead of in an effect.
  if (selectionFor !== expenses) {
    setSelectionFor(expenses)
    setRowSelection({})
  }

  // Leave edit mode for this row only: another row may have been opened while this one was saving.
  const closeEditor = (id: number) => setEditingId((open) => (open === id ? null : open))

  function save(id: number, changes: ExpenseChanges) {
    if (Object.keys(changes).length === 0) return closeEditor(id) // nothing changed: just leave edit mode
    update.mutate(
      { id, changes },
      {
        onSuccess: () => {
          toast.success("Expense updated")
          closeEditor(id)
        },
        onError: (error) => toast.error(messageOf(error)),
      },
    )
  }

  // The column definitions: what each column shows, and how it sorts. useMemo keeps the same
  // array between renders (rebuilding it only when its inputs change), as TanStack recommends.
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
              aria-label={`Select #${row.original.id}`}
              checked={row.getIsSelected()}
              onCheckedChange={(value) => row.toggleSelected(value === true)}
            />
          ),
          enableSorting: false,
        }),
        // The id as "#14": the assistant shows ids the same way, so you can say "delete #14".
        columnHelper.accessor("id", {
          header: ({ column }) => (
            <SortButton title="ID" sorted={column.getIsSorted()} onClick={column.getToggleSortingHandler()} />
          ),
          cell: ({ getValue }) => <span className="text-muted-foreground tabular-nums">#{getValue()}</span>,
          sortFn: sortFn_basic,
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
        columnHelper.accessor((expense) => categoryName(expense.category_id), {
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
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Edit #${row.original.id}`}
                onClick={() => setEditingId(row.original.id)}
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
        }),
      ]),
    [categoryName, deleting, onDelete],
  )

  const table = useTable({
    features,
    columns,
    data: expenses,
    // Use the expense id as the row id, so selection and editing follow the expense, not its position.
    getRowId: (expense) => String(expense.id),
    enableRowSelection: true,
    // "Controlled" selection: the table reads it from our state and reports changes back to us.
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
  })

  const rows = table.getRowModel().rows
  const selected = table.getSelectedRowModel().rows.map((row) => row.original)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex min-h-8 items-center justify-between gap-2 text-sm text-muted-foreground">
        <span>
          {plural(total, "expense")}
          {total > expenses.length && ` · showing the newest ${expenses.length}`}
          {selected.length > 0 && ` · ${selected.length} selected`}
        </span>
        {selected.length > 0 && (
          <Button size="sm" variant="destructive" disabled={deleting} onClick={() => onDelete(selected)}>
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
                  <TableHead key={header.id} aria-sort={pickSort(header.column.getIsSorted())}>
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
                    saving={update.isPending && update.variables?.id === row.original.id}
                    onCancel={() => setEditingId(null)}
                    onSave={(changes) => save(row.original.id, changes)}
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
