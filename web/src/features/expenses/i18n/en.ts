// The "expenses" namespace's English texts: everything the expenses feature shows, grouped by area. Part of
// the expenses feature (i18n/). The source other languages translate (hi.ts); index.ts defines the namespace.
// Not here: what the backend sends (payment-method labels, category names, its error messages) and user data.

/**
 * The expenses feature's texts, in English. {{name}} marks a value filled in when the text is shown; a key ending
 * in _one / _other is one text in two plural forms, picked by `count`.
 */
const en = {
  page: {
    title: "Expenses",
    description: "Add, find, edit and delete your expenses.",
    loadFailed: "Couldn't load your expenses",
  },
  // An expense's fields: the Add dialog's labels, the filters' Category, and the table's column titles.
  fields: {
    id: "ID",
    date: "Date",
    merchant: "Merchant",
    category: "Category",
    amount: "Amount",
    paidWith: "Paid with",
    note: "Note",
    noteOptional: "Note (optional)",
  },
  // The dialogs' buttons.
  actions: {
    cancel: "Cancel",
    save: "Save",
    saving: "Saving…",
    delete: "Delete",
  },
  // The Add expense button and dialog. The examples are the inputs' placeholders.
  add: {
    open: "Add expense",
    title: "Add expense",
    description: "Amounts are in {{currency}}, e.g. {{example}}.",
    merchantExample: "Swiggy",
    noteExample: "Dinner",
    added: "Expense added",
  },
  filters: {
    search: "Search",
    searchPlaceholder: "Merchant or note",
    allCategories: "All categories",
    from: "From",
    to: "To",
    clear: "Clear filters",
  },
  // The count line above the table; its parts are joined with " · ".
  toolbar: {
    count_one: "{{count}} expense",
    count_other: "{{count}} expenses",
    showingNewest: "showing the newest {{shown}}",
    selected_one: "{{count}} selected",
    selected_other: "{{count}} selected",
    deleteSelected: "Delete selected",
  },
  // The table's own texts; its column titles are under "fields".
  table: {
    loading: "Loading…",
    noMatches: "No expenses match these filters.",
    sortBy: "Sort by {{column}}",
    selectAll: "Select all",
    selectRow: "Select #{{id}}",
    actions: "Actions",
    editRow: "Edit #{{id}}",
    deleteRow: "Delete #{{id}}",
  },
  // The inline edit row: each control's name for screen readers, its buttons, and the toast after a save.
  edit: {
    date: "Date of #{{id}}",
    merchant: "Merchant of #{{id}}",
    category: "Category of #{{id}}",
    amount: "Amount of #{{id}}",
    paymentMethod: "Payment method of #{{id}}",
    note: "Note of #{{id}}",
    save: "Save changes to #{{id}}",
    cancel: "Cancel editing #{{id}}",
    updated: "Expense updated",
  },
  // The "are you sure?" dialog before a delete, and the toasts after it.
  delete: {
    titleOne: "Delete this expense?",
    titleSeveral_one: "Delete {{count}} expense?",
    titleSeveral_other: "Delete {{count}} expenses?",
    describeOne: "{{merchant}}, {{amount}} on {{date}}. This can't be undone.",
    describeSeveral: "This can't be undone.",
    deleted_one: "Expense deleted",
    deleted_other: "{{count}} expenses deleted",
    failed_one: "Couldn't delete {{count}}: {{reason}}",
    failed_other: "Couldn't delete {{count}}: {{reason}}",
  },
}

export default en
