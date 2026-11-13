// Display helpers. They only format values for people to read; no arithmetic happens here.

import { CURRENCY_SYMBOLS } from "@/shared/api/contracts.gen"
import { LOCALE } from "@/shared/config/locale"
import { pick } from "@/shared/lib/guards"

const amountFormat = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

// 125000.5 -> "1,25,000.50" (Indian grouping). Number() is fine for *display*: exact values stay in paise.
export function formatAmount(value: number | string): string {
  return amountFormat.format(Number(value))
}

// "125000.5", "INR" -> "₹1,25,000.50"; other currencies -> "1,25,000.50 USD". The backend's
// format_money writes amounts the same way, so the chat's cards and the pages always agree.
export function formatMoney(amount: number | string, currency: string): string {
  const symbol = pick<string>(CURRENCY_SYMBOLS, currency)
  return symbol ? `${symbol}${formatAmount(amount)}` : `${formatAmount(amount)} ${currency}`
}

export function formatCompactMoney(amount: number, currency: string): string {
  // For chart axes: 125000 -> "₹1.3L" style short labels.
  return new Intl.NumberFormat(LOCALE, { style: "currency", currency, notation: "compact" }).format(amount)
}

// "2026-11-13" <-> a Date at local midnight. new Date("2026-11-13") would mean midnight UTC, which is
// still the previous day in some time zones, so dates are built from their parts instead.
export function parseIsoDate(value: unknown): Date | undefined {
  const match = typeof value === "string" ? /^(\d{4})-(\d{2})-(\d{2})/.exec(value) : null
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : undefined
}

export function isoDate(day: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`
}

export function formatDate(value: string | Date): string {
  // "2026-11-13" -> "13 Nov 2026".
  const day = value instanceof Date ? value : parseIsoDate(value)
  return day ? day.toLocaleDateString(LOCALE, { day: "numeric", month: "short", year: "numeric" }) : ""
}

export function formatMonth(isoMonth: string, style: "long" | "short" = "long"): string {
  // "2026-11" -> "November 2026" (long) or "Nov" (short, for chart axes).
  const [year, month] = isoMonth.split("-").map(Number)
  const options: Intl.DateTimeFormatOptions = style === "long" ? { month: "long", year: "numeric" } : { month: "short" }
  return new Date(year, month - 1, 1).toLocaleDateString(LOCALE, options)
}

export function todayIso(): string {
  return isoDate(new Date())
}

export function currentMonth(): string {
  return todayIso().slice(0, 7)
}

export function plural(count: number, word: string, words = `${word}s`): string {
  return `${count} ${count === 1 ? word : words}`
}
