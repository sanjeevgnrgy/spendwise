"use client"

// The pages, as client components the route files can draw. Part of the app composition (app/). The route files
// (page.tsx, and the root not-found.tsx) are server components, so they can export each page's metadata; this
// boundary is where the browser-side app begins (D188). Each feature's page stays lazy (its index.ts), so its code and
// texts load with it.

export { SettingsPage } from "@/features/account"
export { SignInPage } from "@/features/auth"
export { BudgetsPage } from "@/features/budgets"
export { DashboardPage } from "@/features/dashboard"
export { ExpensesPage } from "@/features/expenses"
export { NotFoundPage } from "./placeholder-pages"
