import { Bar, BarChart, XAxis, YAxis } from "recharts"

import type { MonthlySummary } from "@/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { formatMoney, formatMonth } from "@/lib/format"
import { EmptyState } from "@/pages/dashboard/empty-state"

// shadcn charts: the config names each data series and its colour. ChartContainer turns
// `total` into a CSS variable, --color-total, which the bars use (and which follows the theme).
const chartConfig = {
  total: { label: "Spent", color: "var(--primary)" },
} satisfies ChartConfig

export function CategoryChart({ summary }: { summary: MonthlySummary }) {
  // Recharts draws numbers, so convert the backend's paise to rupees for the chart only.
  const rows = summary.by_category.map((c) => ({ name: c.category_name, total: c.total_minor / 100 }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>By category</CardTitle>
        <CardDescription>{formatMonth(summary.month)}</CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <EmptyState message="No spending this month yet." />
        ) : (
          // Horizontal bars: category names stay readable even with many categories.
          <ChartContainer config={chartConfig} className="aspect-auto h-64 w-full">
            <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 8 }} accessibilityLayer>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" width={96} tickLine={false} axisLine={false} />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent formatter={(value) => formatMoney(String(value), summary.currency)} />}
              />
              <Bar dataKey="total" fill="var(--color-total)" radius={4} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
