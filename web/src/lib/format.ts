// Display helpers. They only format values for people to read; no arithmetic happens here.

export function formatMoney(amount: string, currency: string): string {
  // Number() is fine for *display*: the exact value stays in paise on the server.
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(Number(amount))
}

export function formatDate(isoDate: string): string {
  // "2026-11-13" -> "13 Nov 2026". Parsed as a local date, so it never shifts a day across time zones.
  const [year, month, day] = isoDate.split("-").map(Number)
  return new Date(year, month - 1, day).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
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
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
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
