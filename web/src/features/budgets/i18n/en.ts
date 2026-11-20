// The "budgets" namespace's English texts: everything the budgets feature shows, grouped by area. Part of the budgets
// feature (i18n/). The source other languages translate (hi.ts); index.ts defines the namespace.

/** The budgets feature's texts, in English. {{name}} marks a value filled in when the text is shown. */
const en = {
  page: {
    title: "Budgets",
    description: "Monthly limits in {{currency}}, the same every month until you change them.",
    loadFailed: "Couldn't load your budgets",
    previousMonth: "Previous month",
    nextMonth: "Next month",
    elapsed: "{{percent}}% of {{month}} has gone by",
  },
  overall: {
    title: "Overall",
    description: "All your spending in {{month}}",
    noLimit: "No overall limit yet. Set one to see how the month is going.",
  },
  categories: {
    title: "By category",
    description: "Categories with a limit first, the ones closest to it at the top.",
    empty: "There are no categories yet.",
  },
  line: {
    spentOf: "{{spent}} of {{limit}}",
    left: "{{amount}} left",
    over: "{{amount}} over",
    spent: "{{amount}} spent",
    noLimit: "No limit",
    meter: "{{name}}: {{percent}}% of the limit used",
    today: "Today: {{percent}}% of the month",
  },
  states: {
    on_track: "On track",
    near_limit: "Near the limit",
    over_limit: "Over the limit",
  },
  dialog: {
    set: "Set limit",
    change: "Change limit",
    setFor: "Set limit for {{name}}",
    changeFor: "Change limit for {{name}}",
    overallName: "all spending",
    title: "Monthly limit for {{name}}",
    description: "In {{currency}}. It applies every month until you change it.",
    limit: "Monthly limit",
    save: "Save",
    saving: "Saving…",
    cancel: "Cancel",
    remove: "Remove limit",
    removing: "Removing…",
    saved: "Limit saved",
    removed: "Limit removed",
  },
}

export default en
