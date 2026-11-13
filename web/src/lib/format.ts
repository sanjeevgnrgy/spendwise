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
