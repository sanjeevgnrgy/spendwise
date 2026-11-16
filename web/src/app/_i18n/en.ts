// The "app" namespace's English texts: what the app's frame shows (the menu, page names, the top bar, the error
// cards around the page area and the chat). Part of the app composition (app/_i18n/). Other languages translate it.

/** The app frame's texts, in English. {{name}} marks a value filled in when the text is shown. */
const en = {
  menu: "Menu",
  pages: {
    dashboard: "Dashboard",
    expenses: "Expenses",
    budgets: "Budgets",
    settings: "Settings",
    // Only the browser tab's title (the sign-in page has its own heading).
    signIn: "Sign in",
  },
  comingSoon: {
    budgets: "Monthly limits per category will live here.",
  },
  notFound: {
    title: "Page not found",
    description: "There's no page at this address.",
  },
  assistant: {
    open: "Assistant",
    title: "Assistant",
    description: "Chat with the {{app}} assistant.",
  },
  errors: {
    app: "{{app}} hit a problem",
    page: "This page hit a problem",
    assistant: "The assistant hit a problem",
  },
}

export default en
