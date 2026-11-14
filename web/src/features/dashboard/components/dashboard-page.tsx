// A component of the dashboard feature: the Dashboard page, the feature's main export (app/pages.tsx routes to
// it, through the lazy DashboardPage in index.ts). It loads the month's summary, the trend, the newest expenses
// and the category names together, and lays out the stat cards, the two charts and the recent list.

import { useCategories } from "@/features/categories"
import { useExpenses } from "@/features/expenses"
import { DEFAULT_CURRENCY, LIMITS } from "@/shared/api/contracts.gen"
import { RefreshNotice } from "@/shared/components/refresh-notice"
import { SectionError } from "@/shared/components/section-error"
import { messageOf } from "@/shared/lib/errors"
import { currentMonth } from "@/shared/lib/format"
import { queryGroupStatus } from "@/shared/lib/query-status"

import { useTexts } from "../i18n"
import { useMonthlySummary, useMonthlyTrend } from "../queries"
import { CategoryChart } from "./category-chart"
import { DashboardSkeleton } from "./dashboard-skeleton"
import { RecentExpenses } from "./recent-expenses"
import { StatCards } from "./stat-cards"
import { TrendChart } from "./trend-chart"

// How many of the newest expenses the Dashboard lists.
const RECENT_COUNT = 5

/**
 * The Dashboard: this month's numbers, spending by category, the monthly trend and the latest expenses. Until
 * everything has loaded it shows a skeleton, or an error card with Try again (which asks again only what failed).
 * Once loaded, a failed reload keeps the numbers on screen with a "couldn't refresh" notice.
 */
export function DashboardPage() {
  const { t } = useTexts()
  // Small requests, sent at the same time. The backend does the adding up and sends back only totals
  // and 5 rows, not every expense. Each one reloads by itself when the data changes.
  const summary = useMonthlySummary(currentMonth())
  const trend = useMonthlyTrend(LIMITS.trendMonthsDefault)
  const recent = useExpenses({ limit: RECENT_COUNT })
  const categories = useCategories() // the recent list shows category names
  const { failed, retrying, retry } = queryGroupStatus([summary, trend, recent, categories])

  const header = (
    <div>
      <h1 className="text-2xl font-semibold">{t("page.title")}</h1>
      <p className="text-sm text-muted-foreground">{t("page.description", { currency: DEFAULT_CURRENCY })}</p>
    </div>
  )

  // Nothing to show yet: a skeleton while loading, or the error if loading failed. Showing ₹0 when the
  // backend is unreachable would be misleading, so say what happened instead.
  if (!summary.data || !trend.data || !recent.data || !categories.data) {
    return (
      <div className="flex flex-col gap-4">
        {header}
        {failed ? (
          <SectionError
            title={t("page.loadFailed")}
            message={messageOf(failed.error)}
            onRetry={retry}
            retrying={retrying}
          />
        ) : (
          <DashboardSkeleton />
        )}
      </div>
    )
  }

  // Everything has loaded. If a reload has failed since, keep the numbers on screen and say they may be old.
  return (
    <div className="flex flex-col gap-4">
      {header}
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
