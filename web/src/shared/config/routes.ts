// Every page's address, in one place. Part of shared/config, so features can link to a page without importing
// the app. Used by app/pages.tsx (the router and the menu) and by links such as the Dashboard's "View all".

/** Each page's path. A new page gets its address here, then its entry in app/pages.tsx. */
export const ROUTES = {
  dashboard: "/",
  expenses: "/expenses",
  budgets: "/budgets",
  settings: "/settings",
} as const
