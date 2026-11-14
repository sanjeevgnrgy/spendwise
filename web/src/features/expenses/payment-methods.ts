// The expenses feature's payment methods: the list, the default for a new expense, each one's label for people,
// and a check that a string is one of them. Used by expense-form.ts, payment-method-select.tsx (the dropdown)
// and expense-columns.tsx (the table's "Paid with" column).

import { PAYMENT_METHOD_LABELS } from "@/shared/api/contracts.gen"
import { paymentMethodValues } from "@/shared/api/schema.gen"

import type { PaymentMethod } from "./api"

/**
 * Every payment method, in the backend's order (the dropdown lists them so). Both lists (these values and
 * their labels) come from the backend (generated), so the web and the assistant's forms always agree.
 */
export const PAYMENT_METHODS: readonly PaymentMethod[] = paymentMethodValues
/** What a new expense starts with in the Add dialog. */
export const DEFAULT_PAYMENT_METHOD: PaymentMethod = "upi"

/** The method's label for people: "upi" -> "UPI", "netbanking" -> "Net banking". */
export function paymentMethodLabel(method: PaymentMethod): string {
  return PAYMENT_METHOD_LABELS[method]
}

/** Whether a string (like a dropdown's value) is one of the methods; if so, TypeScript treats it as one. */
export function isPaymentMethod(value: string): value is PaymentMethod {
  return PAYMENT_METHODS.some((method) => method === value)
}
