// Every page of the app, listed once: its address, menu title, icon and what it draws. Part of the app
// composition (app/): it's the one place that imports every feature's page. app.tsx builds the routes from PAGES
// and layout/app-sidebar.tsx builds the menu from it, so adding a page is one entry here. The feature pages load
// on first use (each feature's index.ts makes its page lazy; the layout's page area waits for it).

import { LayoutDashboard, PiggyBank, ReceiptText, Settings, type LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { DashboardPage } from "@/features/dashboard"
import { ExpensesPage } from "@/features/expenses"
import { PlaceholderPage } from "@/shared/components/placeholder-page"
import { ROUTES } from "@/shared/config/routes"

/** One page: where it lives, how the menu shows it, and what it draws. */
export interface Page {
  /** Its address, from ROUTES (shared/config/routes.ts). */
  path: string
  /** The menu's label (and a placeholder's heading). */
  title: string
  /** The menu's icon (a lucide-react icon component). */
  icon: LucideIcon
  /** What the router draws at `path`, inside AppLayout's page area. */
  element: ReactNode
}

// A page that isn't built yet: its heading is its menu title. Returns a Page that draws a PlaceholderPage
// with `description`.
function comingSoon(path: string, title: string, icon: LucideIcon, description: string): Page {
  return { path, title, icon, element: <PlaceholderPage title={title} description={description} /> }
}

/**
 * Every page, once: the router (app.tsx) and the menu (app-sidebar.tsx) are both built from this list,
 * so adding a page is one entry here. The menu shows the pages in this order.
 */
export const PAGES: Page[] = [
  { path: ROUTES.dashboard, title: "Dashboard", icon: LayoutDashboard, element: <DashboardPage /> },
  { path: ROUTES.expenses, title: "Expenses", icon: ReceiptText, element: <ExpensesPage /> },
  comingSoon(ROUTES.budgets, "Budgets", PiggyBank, "Monthly limits per category will live here."),
  comingSoon(ROUTES.settings, "Settings", Settings, "Preferences will live here."),
]

/** What an address with no page shows (the catch-all route in app.tsx). It isn't in the menu. */
export const NOT_FOUND = <PlaceholderPage title="Page not found" description="There's no page at this address." />
