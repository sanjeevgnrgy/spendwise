// Every page of the app, listed once: its address, menu name, icon and what it draws. Part of the app
// composition (app/): it's the one place that imports every feature's page. app.tsx builds the routes from PAGES
// and layout/app-sidebar.tsx builds the menu from it, so adding a page is one entry here. The feature pages load
// on first use (each feature's index.ts makes its page lazy; the layout's page area waits for it).

import { LayoutDashboard, PiggyBank, ReceiptText, Settings, type LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { DashboardPage } from "@/features/dashboard"
import { ExpensesPage } from "@/features/expenses"
import { ROUTES } from "@/shared/config/routes"

import type { ComingSoonName, PageName } from "./i18n"
import { ComingSoonPage, NotFoundPage } from "./placeholder-pages"

/** One page: where it lives, how the menu shows it, and what it draws. */
export interface Page {
  /** Its address, from ROUTES (shared/config/routes.ts). */
  path: string
  /** Its name: the menu shows the app text "pages.<name>" (and a placeholder uses it as its heading). */
  name: PageName
  /** The menu's icon (a lucide-react icon component). */
  icon: LucideIcon
  /** What the router draws at `path`, inside AppLayout's page area. */
  element: ReactNode
}

// A page that isn't built yet, with its menu entry (placeholder-pages.tsx draws it).
function comingSoon(path: string, name: ComingSoonName, icon: LucideIcon): Page {
  return { path, name, icon, element: <ComingSoonPage name={name} /> }
}

/**
 * Every page, once: the router (app.tsx) and the menu (app-sidebar.tsx) are both built from this list,
 * so adding a page is one entry here (and its name in app/i18n). The menu shows the pages in this order.
 */
export const PAGES: Page[] = [
  { path: ROUTES.dashboard, name: "dashboard", icon: LayoutDashboard, element: <DashboardPage /> },
  { path: ROUTES.expenses, name: "expenses", icon: ReceiptText, element: <ExpensesPage /> },
  comingSoon(ROUTES.budgets, "budgets", PiggyBank),
  comingSoon(ROUTES.settings, "settings", Settings),
]

/** What an address with no page shows (the catch-all route in app.tsx). It isn't in the menu. */
export const NOT_FOUND = <NotFoundPage />
