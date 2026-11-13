import { LayoutDashboard, PiggyBank, ReceiptText, Settings, type LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

import { DashboardPage } from "@/features/dashboard"
import { ExpensesPage } from "@/features/expenses"
import { PlaceholderPage } from "@/shared/components/placeholder-page"
import { ROUTES } from "@/shared/config/routes"

export interface Page {
  path: string
  title: string // the menu's label (and a placeholder's heading)
  icon: LucideIcon
  element: ReactNode
}

// A page that isn't built yet: its heading is its menu title.
function comingSoon(path: string, title: string, icon: LucideIcon, description: string): Page {
  return { path, title, icon, element: <PlaceholderPage title={title} description={description} /> }
}

// Every page, once: the router (app.tsx) and the menu (app-sidebar.tsx) are both built from this list,
// so adding a page is one entry here.
export const PAGES: Page[] = [
  { path: ROUTES.dashboard, title: "Dashboard", icon: LayoutDashboard, element: <DashboardPage /> },
  { path: ROUTES.expenses, title: "Expenses", icon: ReceiptText, element: <ExpensesPage /> },
  comingSoon(ROUTES.budgets, "Budgets", PiggyBank, "Monthly limits per category will live here."),
  comingSoon(ROUTES.settings, "Settings", Settings, "Preferences will live here."),
]

export const NOT_FOUND = <PlaceholderPage title="Page not found" description="There's no page at this address." />
