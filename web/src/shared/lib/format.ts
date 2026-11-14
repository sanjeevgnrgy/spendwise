// Shared display helpers: money, dates, months and counts, written the way people read them (Indian English, see
// shared/config/locale.ts). They only format values; no arithmetic happens here. Part of shared/lib. Used by every
// page and dialog that shows an amount or a date, and by the assistant's cards and date inputs.

import { CURRENCY_SYMBOLS } from "@/shared/api/contracts.gen"
import { LOCALE } from "@/shared/config/locale"
import { pick } from "@/shared/lib/guards"

// Always two decimals, with the locale's digit grouping. Made once: building a formatter is the slow part.
const amountFormat = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** 125000.5 -> "1,25,000.50" (Indian grouping). Number() is fine for *display*: exact values stay in paise. */
export function formatAmount(value: number | string): string {
  return amountFormat.format(Number(value))
}

/**
 * "125000.5", "INR" -> "₹1,25,000.50"; a currency with no known symbol -> "1,25,000.50 USD". The backend's
 * format_money writes amounts the same way, so the chat's cards and the pages always agree.
 */
export function formatMoney(amount: number | string, currency: string): string {
  const symbol = pick<string>(CURRENCY_SYMBOLS, currency)
  return symbol ? `${symbol}${formatAmount(amount)}` : `${formatAmount(amount)} ${currency}`
}

/** A short money label for chart axes: 125000 -> "₹1.3L" style. */
export function formatCompactMoney(amount: number, currency: string): string {
  return new Intl.NumberFormat(LOCALE, { style: "currency", currency, notation: "compact" }).format(amount)
}

/**
 * "2026-11-13" (or a longer ISO text starting so) -> a Date at local midnight; anything else -> undefined.
 * new Date("2026-11-13") would mean midnight UTC, which is still the previous day in some time zones, so dates
 * are built from their parts instead.
 */
export function parseIsoDate(value: unknown): Date | undefined {
  const match = typeof value === "string" ? /^(\d{4})-(\d{2})-(\d{2})/.exec(value) : null
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : undefined
}

/** A Date -> "2026-11-13", by its local calendar day (the reverse of parseIsoDate). */
export function isoDate(day: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`
}

/** "2026-11-13" (or a Date) -> "13 Nov 2026"; text that isn't a date -> "". */
export function formatDate(value: string | Date): string {
  const day = value instanceof Date ? value : parseIsoDate(value)
  return day ? day.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "numeric" }) : ""
}

/** "2026-11" -> "November 2026" (long) or "Nov" (short, for chart axes). */
export function formatMonth(isoMonth: string, style: "long" | "short" = "long"): string {
  const [year, month] = isoMonth.split("-").map(Number)
  const options: Intl.DateTimeFormatOptions = style === "long" ? { month: "long", year: "numeric" } : { month: "short" }
  return new Date(year, month - 1, 1).toLocaleDateString(LOCALE, options)
}

/** Today, on this device's calendar, as "YYYY-MM-DD" (a new expense's default date). */
export function todayIso(): string {
  return isoDate(new Date())
}

/** This month as "YYYY-MM" (the Dashboard's summary month). */
export function currentMonth(): string {
  return todayIso().slice(0, 7)
}

/** A count and its word: plural(1, "expense") -> "1 expense", plural(3, "category", "categories") -> "3 categories" */
export function plural(count: number, word: string, words = `${word}s`): string {
  return `${count} ${count === 1 ? word : words}`
}
