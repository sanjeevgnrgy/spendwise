// Month arithmetic on "YYYY-MM" strings, as pure functions: the Budgets page's previous and next month. Part of the
// budgets feature.

const MONTHS_PER_YEAR = 12

/** The month `offset` months after `month` (before, if negative): shiftMonth("2026-01", -1) is "2025-12". */
export function shiftMonth(month: string, offset: number): string {
  const [year, number] = month.split("-").map(Number)
  const index = year * MONTHS_PER_YEAR + (number - 1) + offset
  const shiftedYear = Math.floor(index / MONTHS_PER_YEAR)
  const shiftedMonth = (index % MONTHS_PER_YEAR) + 1
  return `${shiftedYear}-${String(shiftedMonth).padStart(2, "0")}`
}
