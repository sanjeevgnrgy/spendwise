// Every page of the menu, listed once: its address, its name and its icon. Part of the app composition (app/).
// layout/app-sidebar.tsx builds the menu from PAGES; the routes themselves are the page.tsx files under (client)/(app)/
// (Next.js's App Router, D188), each drawing its feature's page. Adding a page: its address in ROUTES, its route file,
// its entry here, and its name in app/_i18n.

import { LayoutDashboard, PiggyBank, ReceiptText, Settings, type LucideIcon } from "lucide-react"

import { ROUTES } from "@/shared/config/routes"

import type { PageName } from "../_i18n"

/** One page of the menu: where it lives and how the menu shows it. */
export interface Page {
  /** Its address, from ROUTES (shared/config/routes.ts), the same one its route file serves. */
  path: string
  /** Its name: the menu shows the app text "pages.<name>" (and a placeholder uses it as its heading). */
  name: PageName
  /** The menu's icon (a lucide-react icon component). */
  icon: LucideIcon
}

/** Every page of the menu, in the order the menu shows them. */
export const PAGES: Page[] = [
  { path: ROUTES.dashboard, name: "dashboard", icon: LayoutDashboard },
  { path: ROUTES.expenses, name: "expenses", icon: ReceiptText },
  { path: ROUTES.budgets, name: "budgets", icon: PiggyBank },
  { path: ROUTES.settings, name: "settings", icon: Settings },
]
