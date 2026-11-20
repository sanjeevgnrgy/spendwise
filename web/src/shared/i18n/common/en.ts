// The "common" namespace's English texts: what shared/ itself shows (the API client's errors, the error and refresh
// cards, the placeholder page, the theme and language menus). Part of shared/i18n. The source every other language
// translates (hi.ts); the namespace is defined in index.ts.

/** The shared texts, in English. {{name}} marks a value filled in when the text is shown. */
const en = {
  errors: {
    unexpected: "Something went wrong. Try again; if it keeps happening, reload the page.",
    unreachable: "Can't reach {{app}} right now. Check your connection and try again.",
    unreadable: "The API sent an answer this app couldn't read.",
    requestFailed: "Request failed ({{status}})",
    emptyAnswer: "The API sent an empty answer ({{status}})",
  },
  retry: {
    tryAgain: "Try again",
    tryingAgain: "Trying again…",
    retry: "Retry",
  },
  refreshNotice: {
    stale: "Couldn't refresh, so this may be out of date: {{message}}",
  },
  placeholder: {
    comingSoon: "Coming soon",
  },
  theme: {
    change: "Change theme",
    light: "Light",
    dark: "Dark",
    system: "System",
  },
  // The UI kit's own words (shared/ui): screen-reader labels on its close buttons and the sidebar.
  ui: {
    close: "Close",
    toggleSidebar: "Toggle Sidebar",
    sidebarTitle: "Sidebar",
    sidebarDescription: "Displays the mobile sidebar.",
  },
  // An amount in another currency also shows its INR amount, the one totals count (shared/components/money.tsx).
  money: {
    inBase: "≈ {{amount}}",
    inBaseLabel: "{{amount}} in {{currency}}, at {{rate}} on {{date}}",
  },
  language: {
    change: "Change language",
    loadFailed: "Couldn't switch to {{language}}. Check your connection and try again.",
  },
}

export default en
