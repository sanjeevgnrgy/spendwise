// A component of the budgets feature: one budget's numbers: the bar, "₹4,200 of ₹5,000" and what's left (or how
// much over); or, without a limit, only what was spent. Used by the overall card and the category rows.

import { formatMoney } from "@/shared/lib/format"

import type { BudgetLine } from "../api"
import { useTexts } from "../i18n"
import { BudgetMeter } from "./budget-meter"

// The sign the API puts in front of a negative amount (what's left, once over the limit).
const MINUS = "-"

interface BudgetFiguresProps {
  line: BudgetLine
  currency: string
  /** What the budget is for, for the bar's screen-reader label. */
  name: string
  /** How much of the month has gone by (percent), to mark on the bar; only the overall card shows it. */
  elapsedPercent?: string
}

/** The bar and the two figures under it, or "₹300 spent · No limit" for a line without a budget. */
export function BudgetFigures({ line, currency, name, elapsedPercent }: BudgetFiguresProps) {
  const { t } = useTexts()
  const spent = formatMoney(line.spent, currency)
  if (line.limit == null || line.remaining == null || line.used_percent == null || line.state == null) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("line.spent", { amount: spent })} · {t("line.noLimit")}
      </p>
    )
  }
  const over = line.remaining.startsWith(MINUS)
  const rest = formatMoney(over ? line.remaining.slice(MINUS.length) : line.remaining, currency)
  return (
    <div className="grid gap-1.5">
      <BudgetMeter
        usedPercent={line.used_percent}
        state={line.state}
        label={t("line.meter", { name, percent: line.used_percent })}
        elapsedPercent={elapsedPercent}
        elapsedLabel={elapsedPercent && t("line.today", { percent: elapsedPercent })}
      />
      <div className="flex justify-between gap-2 text-sm text-muted-foreground tabular-nums">
        <span>{t("line.spentOf", { spent, limit: formatMoney(line.limit, currency) })}</span>
        <span className={over ? "text-destructive" : undefined}>
          {t(over ? "line.over" : "line.left", { amount: rest })}
        </span>
      </div>
    </div>
  )
}
