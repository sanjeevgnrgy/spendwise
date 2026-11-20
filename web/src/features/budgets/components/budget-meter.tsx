// A component of the budgets feature: a bar showing how much of a budget is used, coloured by its state, with an
// optional mark for how much of the month has gone by. Public (index.ts): the Dashboard's budget card draws one too.
// It shows no text of its own: the caller gives the label people's screen readers hear.

import { BUDGETS } from "@/shared/api/contracts.gen"
import { pick } from "@/shared/lib/guards"
import { cn } from "@/shared/lib/utils"

import type { BudgetState } from "../api"

// Each state's colour, from a fixed table: the state is only ever used as a key, never pasted into a class name.
const STATE_COLOURS: Readonly<Record<BudgetState, string>> = {
  [BUDGETS.states.on_track]: "bg-primary",
  [BUDGETS.states.near_limit]: "bg-amber-500",
  [BUDGETS.states.over_limit]: "bg-destructive",
}

/** A percentage from the API ("84.0") as a number between 0 and 100, for a width or a position. */
function clampedPercent(value: string): number {
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(Math.max(number, 0), BUDGETS.fullPercent) : 0
}

interface BudgetMeterProps {
  /** The share of the limit used, in percent ("84.0"); above 100 when over. The bar stops at full. */
  usedPercent: string
  state: BudgetState
  /** What screen readers announce, e.g. "Food: 84% of the limit used". */
  label: string
  /** How much of the month has gone by, in percent: drawn as a thin mark, so the bar can be compared with time. */
  elapsedPercent?: string
  /** The mark's tooltip ("Today: 67% of the month"). */
  elapsedLabel?: string
  className?: string
}

/**
 * The bar. Screen readers get a native <progress> (0 to 100) named by `label`; the drawn bar beside it is decoration.
 * Over the limit the bar is full and red.
 */
export function BudgetMeter({ usedPercent, state, label, elapsedPercent, elapsedLabel, className }: BudgetMeterProps) {
  const width = clampedPercent(usedPercent)
  return (
    <div className={cn("relative h-2 w-full rounded-full bg-muted", className)}>
      <progress className="sr-only" value={Math.round(width)} max={BUDGETS.fullPercent} aria-label={label} />
      <div
        aria-hidden
        className={cn("h-full rounded-full", pick(STATE_COLOURS, state))}
        style={{ width: `${width}%` }}
      />
      {elapsedPercent !== undefined && (
        <div
          aria-hidden
          title={elapsedLabel}
          className="absolute -top-1 h-4 w-0.5 rounded bg-foreground/60"
          style={{ left: `${clampedPercent(elapsedPercent)}%` }}
        />
      )}
    </div>
  )
}
