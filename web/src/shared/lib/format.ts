// Shared display helpers: money, dates and months, written the way people read them in the language on now
// (each language's locale is in shared/i18n/languages.ts). They only format values; no arithmetic happens here.
// Part of shared/lib. Used by every page and dialog that shows an amount or a date, and by the assistant's cards and
// date inputs. A component re-renders when the language changes, so its next call uses the new locale.

import { currentLanguageInfo } from "@/shared/i18n"

// The Intl locale of the language on now ("en-IN", "hi-IN").
function locale(): string {
  return currentLanguageInfo().locale
}

// Always two decimals, with the locale's digit grouping. One formatter per locale, made on first use: building a
// formatter is the slow part.
const amountFormats = new Map<string, Intl.NumberFormat>()

/** 125000.5 -> "1,25,000.50" (Indian grouping). Number() is fine for *display*: exact values stay in paise. */
export function formatAmount(value: number | string): string {
  const current = locale()
  let format = amountFormats.get(current)
  if (!format) {
    format = new Intl.NumberFormat(current, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    amountFormats.set(current, format)
  }
  return format.format(Number(value))
}

// Rate formatters, one per locale, made on first use.
const rateFormats = new Map<string, Intl.NumberFormat>()
// A rate keeps up to this many decimals (a cross rate such as 0.0118343195), and no trailing zeros.
const MAX_RATE_DECIMALS = 10

/** "84.5" -> "84.5", "0.0118343195" -> "0.0118343195": an exchange rate, with only the decimals it has. */
export function formatRate(value: string): string {
  const current = locale()
  let format = rateFormats.get(current)
  if (!format) {
    format = new Intl.NumberFormat(current, { maximumFractionDigits: MAX_RATE_DECIMALS })
    rateFormats.set(current, format)
  }
  return format.format(Number(value))
}

// Currency formatters, one per locale and currency, made on first use.
const moneyFormats = new Map<string, Intl.NumberFormat>()

/**
 * "125000.5", "INR" -> "₹1,25,000.50"; "USD" -> "$1,250.50": the currency's CLDR format in the language's locale.
 * The backend's format_money writes amounts from the same CLDR data, so the chat's cards and the pages agree.
 */
export function formatMoney(amount: number | string, currency: string): string {
  const current = locale()
  const cacheKey = `${current}|${currency}`
  let format = moneyFormats.get(cacheKey)
  if (!format) {
    format = new Intl.NumberFormat(current, { style: "currency", currency })
    moneyFormats.set(cacheKey, format)
  }
  return format.format(Number(amount))
}

// Compact currency formatters, one per locale and currency, made on first use (an axis formats every tick).
const compactFormats = new Map<string, Intl.NumberFormat>()

/** A short money label for chart axes: 125000 -> "₹1.3L" style. */
export function formatCompactMoney(amount: number, currency: string): string {
  const current = locale()
  const cacheKey = `${current}|${currency}`
  let format = compactFormats.get(cacheKey)
  if (!format) {
    format = new Intl.NumberFormat(current, { style: "currency", currency, notation: "compact" })
    compactFormats.set(cacheKey, format)
  }
  return format.format(amount)
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
  return day ? day.toLocaleDateString(locale(), { day: "numeric", month: "short", year: "numeric" }) : ""
}

/**
 * A moment with its time zone ("2026-11-15T10:30:00Z", as the API sends timestamps) -> "15 Nov 2026, 4:00 pm", in this
 * device's time zone; text that isn't a moment -> "".
 */
export function formatDateTime(value: string): string {
  const moment = new Date(value)
  if (Number.isNaN(moment.getTime())) return ""
  return moment.toLocaleString(locale(), {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

/** "2026-11" -> "November 2026" (long) or "Nov" (short, for chart axes). */
export function formatMonth(isoMonth: string, style: "long" | "short" = "long"): string {
  const [year, month] = isoMonth.split("-").map(Number)
  const options: Intl.DateTimeFormatOptions = style === "long" ? { month: "long", year: "numeric" } : { month: "short" }
  return new Date(year, month - 1, 1).toLocaleDateString(locale(), options)
}

/** Today, on this device's calendar, as "YYYY-MM-DD" (a new expense's default date). */
export function todayIso(): string {
  return isoDate(new Date())
}

/** This month as "YYYY-MM" (the Dashboard's summary month). */
export function currentMonth(): string {
  return todayIso().slice(0, 7)
}
