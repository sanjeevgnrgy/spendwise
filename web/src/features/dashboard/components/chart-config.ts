// A part of the dashboard feature: the shared configuration of its two charts. Used by category-chart.tsx and
// trend-chart.tsx.

import { useMemo } from "react"

import type { ChartConfig } from "@/shared/ui/chart"

import { useTexts } from "../i18n"

/**
 * shadcn charts: the config names each data series and its colour. ChartContainer turns `total`
 * into a CSS variable, --color-total, which the bars and lines use (and which follows the theme).
 * Both Dashboard charts plot the same thing, money spent, so they share one config. Keep its keys fixed: they
 * become CSS variable names. It's a hook, not a constant, so the series' label follows the language; the same object
 * is returned until the language changes, so the chart doesn't rebuild its styles on every render.
 */
export function useSpentConfig() {
  const { t } = useTexts()
  return useMemo(() => ({ total: { label: t("charts.spent"), color: "var(--primary)" } }) satisfies ChartConfig, [t])
}
