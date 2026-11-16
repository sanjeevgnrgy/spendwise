// Every page's address, in one place. Part of shared/config, so features can link to a page without importing the app.
// Used by app/_frame/pages.tsx (the menu), app/robots.ts and app/sitemap.ts, the sign-in page's gate, and links such as
// the Dashboard's "View all".

import { AUTH } from "@/shared/api/contracts.gen"

/** Each page's path. A new page gets its address here, then its route file under app/ and its menu entry. */
export const ROUTES = {
  dashboard: "/",
  expenses: "/expenses",
  budgets: "/budgets",
  settings: "/settings",
  // The server sends people here when a sign-in fails and after signing out, so the path comes from the contract.
  signIn: AUTH.signInPage,
} as const
