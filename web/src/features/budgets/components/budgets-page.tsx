// A component of the budgets feature: the Budgets page, the feature's main export (its route file,
// app/(client)/(app)/budgets/page.tsx, draws it through the lazy BudgetsPage in index.ts). It loads a month's status
// and lays out the overall card and the categories; the arrows step through the months (the limits stay the same,
// the spending is that month's).

import { ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"

import { DEFAULT_CURRENCY } from "@/shared/api/contracts.gen"
import { RefreshNotice } from "@/shared/components/refresh-notice"
import { SectionError } from "@/shared/components/section-error"
import { messageOf } from "@/shared/lib/errors"
import { currentMonth, formatMonth } from "@/shared/lib/format"
import { Button } from "@/shared/ui/button"
import { Skeleton } from "@/shared/ui/skeleton"

import { useTexts } from "../i18n"
import { shiftMonth } from "../month"
import { useBudgetStatus } from "../queries"
import { CategoryBudgets } from "./category-budgets"
import { OverallCard } from "./overall-card"

/**
 * The Budgets page. Until the status has loaded it shows a skeleton, or an error card with Try again; once loaded, a
 * failed reload keeps the figures on screen with a "couldn't refresh" notice.
 */
export function BudgetsPage() {
  const { t } = useTexts()
  const [month, setMonth] = useState(currentMonth)
  const status = useBudgetStatus(month)
  const retry = () => void status.refetch()
  const step = (offset: number) => () => setMonth(shiftMonth(month, offset))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">{t("page.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("page.description", { currency: DEFAULT_CURRENCY })}</p>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label={t("page.previousMonth")} onClick={step(-1)}>
            <ChevronLeft />
          </Button>
          <span aria-live="polite" className="min-w-32 text-center text-sm font-medium">
            {formatMonth(month)}
          </span>
          <Button variant="ghost" size="icon" aria-label={t("page.nextMonth")} onClick={step(1)}>
            <ChevronRight />
          </Button>
        </div>
      </div>
      {status.data ? (
        <>
          {status.isError && (
            <RefreshNotice message={messageOf(status.error)} onRetry={retry} retrying={status.isFetching} />
          )}
          <OverallCard status={status.data} />
          <CategoryBudgets status={status.data} />
        </>
      ) : status.isError ? (
        <SectionError
          title={t("page.loadFailed")}
          message={messageOf(status.error)}
          onRetry={retry}
          retrying={status.isFetching}
        />
      ) : (
        <div className="grid gap-4">
          <Skeleton className="h-36" />
          <Skeleton className="h-64" />
        </div>
      )}
    </div>
  )
}
