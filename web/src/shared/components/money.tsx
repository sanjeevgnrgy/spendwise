// A shared component: an expense's amount in its own currency and, when that isn't INR, the INR amount it's stored
// with too (D204), the one every total counts. Part of shared/. Used by the Expenses table and the Dashboard's recent
// expenses.

import { useTranslation } from "react-i18next"

import { DEFAULT_CURRENCY } from "@/shared/api/contracts.gen"
import { formatDate, formatMoney, formatRate } from "@/shared/lib/format"

interface ExpenseMoneyProps {
  /** The amount in its own currency (a decimal string from the API). */
  amount: string
  currency: string
  /** The same amount in INR; null for an expense in another currency that hasn't been converted. */
  baseAmount: string | null
  /** The rate it was converted at, and that rate's day (ISO date). */
  rate: string | null
  rateDate: string | null
}

/**
 * "$4.00", with "≈ ₹338.00" under it for an amount not in INR; its title says the rate and the day. An INR amount, or
 * one not converted yet, is shown alone.
 */
export function ExpenseMoney({ amount, currency, baseAmount, rate, rateDate }: ExpenseMoneyProps) {
  const { t } = useTranslation()
  const own = formatMoney(amount, currency)
  if (currency === DEFAULT_CURRENCY || baseAmount === null || rate === null || rateDate === null) {
    return <span>{own}</span>
  }
  const inBase = formatMoney(baseAmount, DEFAULT_CURRENCY)
  const label = t("money.inBaseLabel", {
    amount: inBase,
    currency: DEFAULT_CURRENCY,
    rate: formatRate(rate),
    date: formatDate(rateDate),
  })
  return (
    <span className="inline-flex flex-col items-end leading-tight" title={label}>
      <span>{own}</span>
      <span className="text-xs text-muted-foreground">{t("money.inBase", { amount: inBase })}</span>
    </span>
  )
}
