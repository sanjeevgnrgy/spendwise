import { useCategories } from "@/features/categories"
import { useExpenses } from "@/features/expenses"
import { DEFAULT_CURRENCY, LIMITS } from "@/shared/api/contracts.gen"
import { RefreshNotice } from "@/shared/components/refresh-notice"
import { SectionError } from "@/shared/components/section-error"
import { messageOf } from "@/shared/lib/errors"
import { currentMonth } from "@/shared/lib/format"

import { useMonthlySummary, useMonthlyTrend } from "../queries"
import { CategoryChart } from "./category-chart"
import { DashboardSkeleton } from "./dashboard-skeleton"
import { RecentExpenses } from "./recent-expenses"
import { StatCards } from "./stat-cards"
import { TrendChart } from "./trend-chart"

// How many of the newest expenses the Dashboard lists.
const RECENT_COUNT = 5

export function DashboardPage() {
  // Small requests, sent at the same time. The backend does the adding up and sends back only totals
  // and 5 rows, not every expense. Each one reloads by itself when the data changes.
  const summary = useMonthlySummary(currentMonth())
  const trend = useMonthlyTrend(LIMITS.trendMonthsDefault)
  const recent = useExpenses({ limit: RECENT_COUNT })
  const categories = useCategories() // the recent list shows category names
  const queries = [summary, trend, recent, categories]
  const failed = queries.find((query) => query.isError)
  const retrying = queries.some((query) => query.isFetching)
  // Only the requests that failed are asked again.
  const retry = () => queries.filter((query) => query.isError).forEach((query) => query.refetch())

  const header = (
    <div>
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="text-sm text-muted-foreground">Your spending at a glance (amounts in {DEFAULT_CURRENCY}).</p>
    </div>
  )

  // Nothing to show yet: a skeleton while loading, or the error if loading failed. Showing ₹0 when the
  // backend is unreachable would be misleading, so say what happened instead.
  if (!summary.data || !trend.data || !recent.data || !categories.data) {
    return (
      <div className="flex flex-col gap-4">
        {header}
        {failed ? (
          <SectionError title="Couldn't load the dashboard" message={messageOf(failed.error)} onRetry={retry} retrying={retrying} />
        ) : (
          <DashboardSkeleton />
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {header}
      {/* Everything loaded once, but a reload failed: keep the numbers on screen and say they may be old. */}
      {failed && <RefreshNotice message={messageOf(failed.error)} onRetry={retry} retrying={retrying} />}
      <StatCards summary={summary.data} />
      <div className="grid gap-4 lg:grid-cols-2">
        <CategoryChart summary={summary.data} />
        <TrendChart trend={trend.data} />
      </div>
      <RecentExpenses expenses={recent.data.items} />
    </div>
  )
}
