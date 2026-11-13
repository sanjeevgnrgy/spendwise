import { Minus, TrendingDown, TrendingUp } from "lucide-react"
import { Bar, BarChart, Cell, Line, LineChart, Pie, PieChart, XAxis } from "recharts"

import { A2UI } from "@/shared/api/contracts.gen"
import { LOCALE } from "@/shared/config/locale"
import { formatAmount } from "@/shared/lib/format"
import { isObject } from "@/shared/lib/guards"
import { Card, CardContent } from "@/shared/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/shared/ui/chart"

import { Unsupported } from "./a2ui-unsupported"
import type { A2uiComponent } from "./protocol"

// SpendWise's insights catalog (urn:spendwise:catalog:insights:v1): Chart and Stat. The agent sends
// only data and labels; every colour, size and style is decided here.

// A FIXED chart config. shadcn's ChartContainer writes the config's keys and colours into a <style>
// tag, so nothing from the agent may ever become a key or a colour: its labels are only drawn as text.
const CONFIG = { value: { label: "Amount", color: "var(--chart-1)" } } satisfies ChartConfig
// The theme's five chart colours, for donut slices (more slices simply reuse them).
const SLICE_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"]
const { chartTypes: CHART, trends: TREND, maxChartPoints, maxUnitLength } = A2UI.insights

interface Point {
  label: string
  value: number
}

function isPoint(value: unknown): value is Point {
  return isObject(value) && typeof value.label === "string" && typeof value.value === "number" && Number.isFinite(value.value)
}

// Keep only well-formed points, and copy just the two fields a chart uses.
function readPoints(data: unknown): Point[] {
  if (!Array.isArray(data)) return []
  return data
    .filter(isPoint)
    .slice(0, maxChartPoints)
    .map((p) => ({ label: p.label, value: p.value }))
}

export function A2uiInsight({ node }: { node: A2uiComponent }) {
  switch (node.component) {
    case A2UI.components.Chart:
      return <A2uiChart node={node} />
    case A2UI.components.Stat:
      return <A2uiStat node={node} />
    default:
      return <Unsupported what={`a "${node.component}" component`} />
  }
}

function A2uiChart({ node }: { node: A2uiComponent }) {
  const points = readPoints(node.data)
  if (points.length === 0) return <Unsupported what="a chart without data" />
  const unit = typeof node.unit === "string" ? node.unit.slice(0, maxUnitLength) : ""
  // With a unit (money): grouped with two decimals, exactly like the amounts the server writes in the
  // same card ("₹2,340.00"), so a number never appears in two styles side by side.
  const format = (value: unknown) =>
    unit ? `${unit}${formatAmount(Number(value))}` : Number(value).toLocaleString(LOCALE, { maximumFractionDigits: 2 })

  switch (node.chartType) {
    case CHART.bar:
      return (
        <ChartContainer config={CONFIG} className="aspect-auto h-40 w-full">
          <BarChart data={points} accessibilityLayer>
            <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} fontSize={10} />
            <ChartTooltip cursor={false} content={<ChartTooltipContent formatter={format} />} />
            <Bar dataKey="value" fill="var(--color-value)" radius={4} />
          </BarChart>
        </ChartContainer>
      )
    case CHART.line:
      return (
        <ChartContainer config={CONFIG} className="aspect-auto h-40 w-full">
          <LineChart data={points} margin={{ left: 8, right: 8, top: 8 }} accessibilityLayer>
            <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={10} />
            <ChartTooltip content={<ChartTooltipContent formatter={format} />} />
            <Line dataKey="value" type="monotone" stroke="var(--color-value)" strokeWidth={2} dot={false} />
          </LineChart>
        </ChartContainer>
      )
    case CHART.donut:
      return (
        <div className="flex items-center gap-3">
          <ChartContainer config={CONFIG} className="aspect-square h-28 shrink-0">
            <PieChart>
              <Pie data={points} dataKey="value" nameKey="label" innerRadius="55%" strokeWidth={2}>
                {points.map((point, index) => (
                  <Cell key={`${index}-${point.label}`} fill={SLICE_COLORS[index % SLICE_COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ChartContainer>
          {/* The legend is also the chart's text version: every slice with its value, for screen readers too. */}
          <ul className="flex min-w-0 flex-1 flex-col gap-1 text-xs">
            {points.map((point, index) => (
              <li key={`${index}-${point.label}`} className="flex items-center gap-1.5">
                <span
                  className="size-2 shrink-0 rounded-full"
                  style={{ backgroundColor: SLICE_COLORS[index % SLICE_COLORS.length] }}
                />
                <span className="truncate">{point.label}</span>
                <span className="ml-auto text-muted-foreground tabular-nums">{format(point.value)}</span>
              </li>
            ))}
          </ul>
        </div>
      )
    default:
      return <Unsupported what="this kind of chart" />
  }
}

// The arrow only shows direction. It isn't coloured red or green: whether "up" is good depends on what's measured.
function TrendIcon({ trend }: { trend: unknown }) {
  const className = "size-3 shrink-0"
  switch (trend) {
    case TREND.up:
      return <TrendingUp className={className} />
    case TREND.down:
      return <TrendingDown className={className} />
    case TREND.flat:
      return <Minus className={className} />
    default:
      return null
  }
}

// One number worth noticing, as a small card: label, value, and how it changed.
function A2uiStat({ node }: { node: A2uiComponent }) {
  const text = (value: unknown) => (typeof value === "string" ? value : "")
  const change = text(node.change)
  return (
    <Card size="sm" className="min-w-0 flex-1 gap-1">
      <CardContent className="flex flex-col gap-0.5">
        <span className="text-xs text-muted-foreground">{text(node.label)}</span>
        <span className="truncate text-base font-semibold tabular-nums">{text(node.value)}</span>
        {change && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <TrendIcon trend={node.trend} />
            {change}
          </span>
        )}
      </CardContent>
    </Card>
  )
}
