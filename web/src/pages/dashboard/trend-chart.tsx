import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import type { MonthlyTrend } from "@/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { formatCompactMoney, formatMoney, formatMonth } from "@/lib/format"
import { EmptyState } from "@/pages/dashboard/empty-state"

const chartConfig = {
  total: { label: "Spent", color: "var(--primary)" },
} satisfies ChartConfig

export function TrendChart({ trend }: { trend: MonthlyTrend }) {
  // The backend already filled empty months with 0, so the line has a point for every month.
  const rows = trend.months.map((m) => ({
    label: formatMonth(m.month, "short"),
    fullLabel: formatMonth(m.month),
    total: m.total_minor / 100,
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
          <EmptyState message={`No spending in the last ${trend.months.length} months.`} />
        ) : (
          <ChartContainer config={chartConfig} className="aspect-auto h-64 w-full">
            <LineChart data={rows} margin={{ left: 4, right: 12, top: 8 }} accessibilityLayer>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
              <YAxis width={56} tickLine={false} axisLine={false} tickFormatter={formatCompactMoney} />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel}
                    formatter={(value) => formatMoney(String(value), trend.currency)}
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
