import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import { EmptyState } from "@/shared/components/empty-state"
import { ROUTES } from "@/shared/config/routes"
import { formatCompactMoney, formatMoney, formatMonth } from "@/shared/lib/format"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/shared/ui/chart"

import type { MonthlyTrend } from "../api"
import { SPENT_CONFIG } from "./chart-config"

const MONEY_AXIS_WIDTH = 56

export function TrendChart({ trend }: { trend: MonthlyTrend }) {
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
        <CardTitle>Monthly trend</CardTitle>
        <CardDescription>Last {trend.months.length} months</CardDescription>
      </CardHeader>
      <CardContent>
        {nothingSpent ? (
          <EmptyState
            message={`No spending in the last ${trend.months.length} months.`}
            action={{ label: "Add an expense", to: ROUTES.expenses }}
          />
        ) : (
          <ChartContainer config={SPENT_CONFIG} className="aspect-auto h-64 w-full">
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
