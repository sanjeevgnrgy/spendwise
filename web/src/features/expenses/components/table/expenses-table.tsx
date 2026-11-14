// A component of the expenses feature: the expenses table (TanStack Table), with the count line above it, sortable
// headers, tick boxes, Edit and Delete on each row, and the inline edit row. It puts together the parts: the
// columns (expense-columns.tsx), the count line (expenses-toolbar.tsx), inline editing (use-expense-editor.ts) and
// the row selection kept here. Deleting goes through the page, which asks "are you sure?" first.
// Used by the Expenses page.

import { flexRender, useTable, type Row, type RowSelectionState } from "@tanstack/react-table"
import { useMemo, useState } from "react"

import { useCategoryName } from "@/features/categories"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

import type { Expense } from "../../api"
import { useIsDeletingExpenses } from "../../queries"
import { EditRow } from "./edit-row"
import { ariaSortOf, expenseColumns, expenseTableFeatures } from "./expense-columns"
import { ExpensesToolbar } from "./expenses-toolbar"
import { useExpenseEditor, type ExpenseEditor } from "./use-expense-editor"

interface ExpensesTableProps {
  /** The rows to show (the newest first, as the API sends them). */
  expenses: Expense[]
  /** How many match the filters; `expenses` may hold fewer (the API's limit). */
  total: number
  /** Nothing has loaded yet: an empty table says "Loading…". */
  loading: boolean
  /** Asks the page to confirm and delete these expenses (one row, or all selected rows). */
  onDelete: (expenses: Expense[]) => void
}

// Which rows are ticked, as { "12": true, "15": true }. Kept here (not only inside the table) so the table
// decides when it's cleared: new data (after a filter change, add, edit or delete) clears it, so hidden or
// already-deleted rows can't stay selected by accident. React's "reset state when a prop changes" pattern:
// compare during render instead of in an effect.
function useSelectionOf(expenses: Expense[]) {
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [selectionFor, setSelectionFor] = useState(expenses)
  if (selectionFor !== expenses) {
    setSelectionFor(expenses)
    setRowSelection({})
  }
  return [rowSelection, setRowSelection] as const
}

/**
 * The expenses as a table: a count line ("140 expenses · showing the newest 100 · 2 selected"), then one row per
 * expense. Clicking a header sorts by id, date, merchant, category or amount; sorting happens in the browser,
 * within the rows already loaded. The row being edited is drawn as an EditRow. While a delete runs, every
 * delete button is disabled.
 */
export function ExpensesTable({ expenses, total, loading, onDelete }: ExpensesTableProps) {
  const editor = useExpenseEditor()
  // A delete is running (the confirmation dialog started it): its rows can't be deleted twice meanwhile.
  const deleting = useIsDeletingExpenses()
  const categoryName = useCategoryName()
  const [rowSelection, setRowSelection] = useSelectionOf(expenses)
  // The same function on every render (React's state setter), so it never makes the columns rebuild.
  const onEdit = editor.start

  // useMemo keeps the same columns between renders, rebuilding them only when their inputs change, as TanStack
  // recommends. onDelete is the page's state setter, so it's stable too.
  const columns = useMemo(
    () => expenseColumns({ categoryName, deleting, onEdit, onDelete }),
    [categoryName, deleting, onEdit, onDelete],
  )

  const table = useTable({
    features: expenseTableFeatures,
    columns,
    data: expenses,
    // Use the expense id as the row id, so selection and editing follow the expense, not its position.
    getRowId: (expense) => String(expense.id),
    enableRowSelection: true,
    // "Controlled" selection: the table reads it from our state and reports changes back to us.
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
  })

  // The ticked expenses, for the count and Delete selected.
  const selected = table.getSelectedRowModel().rows.map((row) => row.original)

  // Each header cell says how it's sorted (aria-sort).
  return (
    <div className="flex flex-col gap-2">
      <ExpensesToolbar
        total={total}
        shown={expenses.length}
        selected={selected.length}
        deleting={deleting}
        onDeleteSelected={() => onDelete(selected)}
      />

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} aria-sort={ariaSortOf(header.column.getIsSorted())}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <ExpenseRows rows={table.getRowModel().rows} columnCount={columns.length} loading={loading} editor={editor} />
        </Table>
      </div>
    </div>
  )
}

interface ExpenseRowsProps {
  // The rows in their current (sorted) order.
  rows: Row<typeof expenseTableFeatures, Expense>[]
  // How many columns the "nothing here" cell spans.
  columnCount: number
  loading: boolean
  editor: ExpenseEditor
}

// The table's body: one row per expense, the one being edited drawn as an EditRow. With no rows, one wide cell
// says "Loading…" or that nothing matches the filters. getAllCells, not getVisibleCells: v9 only has
// getVisibleCells with the column-visibility feature, which this table doesn't use.
function ExpenseRows({ rows, columnCount, loading, editor }: ExpenseRowsProps) {
  return (
    <TableBody>
      {rows.length === 0 ? (
        <TableRow>
          <TableCell colSpan={columnCount} className="h-24 text-center text-muted-foreground">
            {loading ? "Loading…" : "No expenses match these filters."}
          </TableCell>
        </TableRow>
      ) : (
        rows.map((row) =>
          row.original.id === editor.editingId ? (
            <EditRow
              key={row.id}
              expense={row.original}
              saving={editor.isSaving(row.original.id)}
              onCancel={editor.cancel}
              onSave={(changes) => editor.save(row.original.id, changes)}
            />
          ) : (
            <TableRow key={row.id} data-state={row.getIsSelected() ? "selected" : undefined}>
              {row.getAllCells().map((cell) => (
                <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
              ))}
            </TableRow>
          ),
        )
      )}
    </TableBody>
  )
}
