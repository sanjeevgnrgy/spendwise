import { Route, Routes } from "react-router"

import { AppLayout } from "@/components/app-layout"
import { PlaceholderPage } from "@/components/placeholder-page"
import { ExpensesPage } from "@/pages/expenses/expenses-page"

// URL -> page. Every page is nested inside AppLayout, so they all share the sidebar and top bar.
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<PlaceholderPage title="Dashboard" description="Monthly totals and charts will appear here." />} />
        <Route path="expenses" element={<ExpensesPage />} />
        <Route path="budgets" element={<PlaceholderPage title="Budgets" description="Monthly limits per category will live here." />} />
        <Route path="settings" element={<PlaceholderPage title="Settings" description="Preferences will live here." />} />
        <Route path="*" element={<PlaceholderPage title="Page not found" description="There's no page at this address." />} />
      </Route>
    </Routes>
  )
}
