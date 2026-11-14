// The "dashboard" namespace's English texts: everything the dashboard feature shows, grouped by area. Part of
// the dashboard feature (i18n/). The source other languages translate (hi.ts); index.ts defines the namespace.

/**
 * The dashboard feature's texts, in English. {{name}} marks a value filled in when the text is shown. A key ending in
 * _zero, _one or _other is one form of a counted text: t("stats.categoriesUsed", { count }) picks the form.
 */
const en = {
  page: {
    title: "Dashboard",
    description: "Your spending at a glance (amounts in {{currency}}).",
    loadFailed: "Couldn't load the dashboard",
  },
  stats: {
    spentIn: "Spent in {{month}}",
    noExpensesThisMonth: "No expenses yet this month",
    totalOfMonth: "Total of this month's expenses",
    expensesThisMonth: "Expenses this month",
    categoriesUsed_one: "{{count}} category used",
    categoriesUsed_other: "{{count}} categories used",
    topCategory: "Top category",
    topAcross_one: "{{amount}} across {{count}} expense",
    topAcross_other: "{{amount}} across {{count}} expenses",
    nothingSpent: "Nothing spent yet",
  },
  byCategory: {
    title: "By category",
    empty: "No spending this month yet.",
  },
  trend: {
    title: "Monthly trend",
    lastMonths_one: "Last {{count}} month",
    lastMonths_other: "Last {{count}} months",
    empty_one: "No spending in the last {{count}} month.",
    empty_other: "No spending in the last {{count}} months.",
  },
  recent: {
    title: "Recent expenses",
    latest_zero: "The latest you recorded",
    latest_one: "The latest {{count}} you recorded",
    latest_other: "The latest {{count}} you recorded",
    viewAll: "View all",
    empty: "No expenses yet.",
  },
  charts: {
    spent: "Spent",
  },
  addExpense: "Add an expense",
}

export default en
