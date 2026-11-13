import { RefreshCw } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import {
  getMonthlySummary,
  getMonthlyTrend,
  listCategories,
  listExpenses,
  type Category,
  type Expense,
  type MonthlySummary,
  type MonthlyTrend,
} from "@/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useDataSync } from "@/lib/data-sync"
import { currentMonth } from "@/lib/format"
import { CategoryChart } from "@/pages/dashboard/category-chart"
import { DashboardSkeleton } from "@/pages/dashboard/dashboard-skeleton"
import { RecentExpenses } from "@/pages/dashboard/recent-expenses"
import { StatCards } from "@/pages/dashboard/stat-cards"
import { TrendChart } from "@/pages/dashboard/trend-chart"

interface DashboardData {
  summary: MonthlySummary
  trend: MonthlyTrend
  recent: Expense[]
  categories: Category[]
}

export function DashboardPage() {
  // null = still loading (show skeletons); an error message = loading failed.
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)
  // Goes up when the chat assistant changes expenses: the effect below reloads the numbers.
  const { dataVersion } = useDataSync()
  const month = currentMonth()

  useEffect(() => {
    let cancelled = false
    // Four small requests, sent at the same time. The backend does the adding up and sends back
    // only totals and 5 rows, not every expense.
    Promise.all([getMonthlySummary(month), getMonthlyTrend(6), listExpenses({ limit: 5 }), listCategories()])
      .then(([summary, trend, recent, categories]) => {
        if (!cancelled) setData({ summary, trend, recent, categories })
      })
      .catch((err) => {
        if (cancelled) return
        const message = err instanceof Error ? err.message : String(err)
        setError(message)
        toast.error(message)
      })
    // Clean-up: ignore the answer if the page was left (or reloaded) before it arrived.
    return () => {
      cancelled = true
    }
  }, [month, reloadCount, dataVersion])

  function retry() {
    setError(null)
    setData(null)
    setReloadCount((count) => count + 1)
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Your spending at a glance (amounts in INR).</p>
      </div>

      {error ? (
        // Showing ₹0 when the backend is unreachable would be misleading, so say what happened instead.
        <Card>
          <CardHeader>
            <CardTitle>Couldn't load the dashboard</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={retry}>
              <RefreshCw /> Try again
            </Button>
          </CardContent>
        </Card>
      ) : data === null ? (
        <DashboardSkeleton />
      ) : (
        <>
          <StatCards summary={data.summary} />
          <div className="grid gap-4 lg:grid-cols-2">
            <CategoryChart summary={data.summary} />
            <TrendChart trend={data.trend} />
          </div>
          <RecentExpenses expenses={data.recent} categories={data.categories} />
        </>
      )}
    </div>
  )
}
