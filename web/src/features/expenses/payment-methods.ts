import { PAYMENT_METHOD_LABELS } from "@/shared/api/contracts.gen"
import { paymentMethodValues } from "@/shared/api/schema.gen"

import type { PaymentMethod } from "./api"

// Both lists come from the backend (generated), so the web and the assistant's forms always agree.
export const PAYMENT_METHODS: readonly PaymentMethod[] = paymentMethodValues
export const DEFAULT_PAYMENT_METHOD: PaymentMethod = "upi"

export function paymentMethodLabel(method: PaymentMethod): string {
  return PAYMENT_METHOD_LABELS[method]
}

export function isPaymentMethod(value: string): value is PaymentMethod {
  return PAYMENT_METHODS.some((method) => method === value)
}
