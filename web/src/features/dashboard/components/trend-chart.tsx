// A component of the dashboard feature: the "Monthly trend" card, a line chart of the last few months' spending
// (shadcn charts over Recharts). Used by the Dashboard page.

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import { EmptyState } from "@/shared/components/empty-state"
import { ROUTES } from "@/shared/config/routes"
import { formatCompactMoney, formatMoney, formatMonth } from "@/shared/lib/format"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/shared/ui/chart"

import type { MonthlyTrend } from "../api"
import { useTexts } from "../i18n"
import { useSpentConfig } from "./chart-config"

// Room for the money labels beside the chart ("₹1.3L"), in pixels.
const MONEY_AXIS_WIDTH = 56

/**
 * "Monthly trend": the total spent in each of the last few months as a line, short month names on the axis and the
 * full month and amount on hover. If nothing was spent in any of them, it says so and offers a link to add one.
 */
export function TrendChart({ trend }: { trend: MonthlyTrend }) {
  const { t } = useTexts()
  const config = useSpentConfig()
  // How many months the chart covers: the backend sends every one, so this is the trend's length.
  const count = trend.months.length
  // The backend already filled empty months with 0, so the line has a point for every month.
  const rows = trend.months.map((m) => ({
    label: formatMonth(m.month, "short"),
    fullLabel: formatMonth(m.month),
    total: Number(m.total),
  }))
  const nothingSpent = trend.months.every((m) => m.total_minor === 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("trend.title")}</CardTitle>
        <CardDescription>{t("trend.lastMonths", { count })}</CardDescription>
      </CardHeader>
      <CardContent>
        {nothingSpent ? (
          <EmptyState message={t("trend.empty", { count })} action={{ label: t("addExpense"), to: ROUTES.expenses }} />
        ) : (
          <ChartContainer config={config} className="aspect-auto h-64 w-full">
            <LineChart data={rows} margin={{ left: 4, right: 12, top: 8 }} accessibilityLayer>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
              <YAxis
                width={MONEY_AXIS_WIDTH}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value: number) => formatCompactMoney(value, trend.currency)}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel}
                    formatter={(value) => formatMoney(Number(value), trend.currency)}
                  />
                }
              />
              <Line dataKey="total" type="monotone" stroke="var(--color-total)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
