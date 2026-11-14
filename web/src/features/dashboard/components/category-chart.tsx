// A component of the dashboard feature: the "By category" card, a bar chart of this month's spending per category
// (shadcn charts over Recharts). Used by the Dashboard page.

import { Bar, BarChart, XAxis, YAxis } from "recharts"

import { EmptyState } from "@/shared/components/empty-state"
import { ROUTES } from "@/shared/config/routes"
import { formatMoney, formatMonth } from "@/shared/lib/format"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/shared/ui/chart"

import type { MonthlySummary } from "../api"
import { useTexts } from "../i18n"
import { useSpentConfig } from "./chart-config"

// Room for the category names beside the bars, in pixels.
const CATEGORY_AXIS_WIDTH = 96

/**
 * "By category": this month's spending per category as horizontal bars, biggest first (the backend's order), with
 * the amount on hover. With nothing spent yet, it says so and offers a link to add an expense.
 */
export function CategoryChart({ summary }: { summary: MonthlySummary }) {
  const { t } = useTexts()
  const config = useSpentConfig()
  // Recharts draws numbers: the API's rupee string ("450.50") becomes 450.5, for the chart only.
  const rows = summary.by_category.map((c) => ({ name: c.category_name, total: Number(c.total) }))

  // Horizontal bars: category names stay readable even with many categories.
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("byCategory.title")}</CardTitle>
        <CardDescription>{formatMonth(summary.month)}</CardDescription>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <EmptyState message={t("byCategory.empty")} action={{ label: t("addExpense"), to: ROUTES.expenses }} />
        ) : (
          <ChartContainer config={config} className="aspect-auto h-64 w-full">
            <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 8 }} accessibilityLayer>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" width={CATEGORY_AXIS_WIDTH} tickLine={false} axisLine={false} />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent formatter={(value) => formatMoney(Number(value), summary.currency)} />}
              />
              <Bar dataKey="total" fill="var(--color-total)" radius={4} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
