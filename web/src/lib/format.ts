// Display helpers. They only format values for people to read; no arithmetic happens here.

export function formatMoney(amount: string, currency: string): string {
  // Number() is fine for *display*: the exact value stays in paise on the server.
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(Number(amount))
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
  return day ? day.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : ""
}

export function formatMonth(isoMonth: string, style: "long" | "short" = "long"): string {
  // "2026-11" -> "November 2026" (long) or "Nov" (short, for chart axes).
  const [year, month] = isoMonth.split("-").map(Number)
  const options: Intl.DateTimeFormatOptions = style === "long" ? { month: "long", year: "numeric" } : { month: "short" }
  return new Date(year, month - 1, 1).toLocaleDateString("en-IN", options)
}

export function formatCompactMoney(amount: number): string {
  // For chart axes: 125000 -> "₹1.3L" style short labels.
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", notation: "compact" }).format(amount)
}

export function currentMonth(): string {
  return todayIso().slice(0, 7)
}

export function todayIso(): string {
  return isoDate(new Date())
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Cash",
  upi: "UPI",
  card: "Card",
  netbanking: "Net banking",
  wallet: "Wallet",
  other: "Other",
}

export function paymentMethodLabel(method: string): string {
  return PAYMENT_METHOD_LABELS[method] ?? method
}
