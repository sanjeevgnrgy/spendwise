// A part of the dashboard feature: the shared configuration of its two charts. Used by category-chart.tsx and
// trend-chart.tsx.

import type { ChartConfig } from "@/shared/ui/chart"

/**
 * shadcn charts: the config names each data series and its colour. ChartContainer turns `total`
 * into a CSS variable, --color-total, which the bars and lines use (and which follows the theme).
 * Both Dashboard charts plot the same thing, money spent, so they share one config. Keep it fixed: its keys
 * become CSS variable names.
 */
export const SPENT_CONFIG = {
  total: { label: "Spent", color: "var(--primary)" },
} satisfies ChartConfig
