// A component of the budgets feature: a small badge naming a budget's state ("Near the limit"). Used by the overall
// card and the category rows.

import { BUDGETS } from "@/shared/api/contracts.gen"
import { pick } from "@/shared/lib/guards"
import { Badge } from "@/shared/ui/badge"

import type { BudgetState } from "../api"
import { useTexts } from "../i18n"

// Each state's badge style, from a fixed table.
const STATE_VARIANTS: Readonly<Record<BudgetState, "secondary" | "outline" | "destructive">> = {
  [BUDGETS.states.on_track]: "secondary",
  [BUDGETS.states.near_limit]: "outline",
  [BUDGETS.states.over_limit]: "destructive",
}

/** The state's name, in a badge styled for it. */
export function BudgetStateBadge({ state }: { state: BudgetState }) {
  const { t } = useTexts()
  return <Badge variant={pick(STATE_VARIANTS, state)}>{t(`states.${state}`)}</Badge>
}
