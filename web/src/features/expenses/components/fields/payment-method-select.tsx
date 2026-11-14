// A component of the expenses feature: the payment-method dropdown (shadcn's Select), listing every method
// by its label. Used by the Add dialog and the inline edit row.

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

import type { PaymentMethod } from "../../api"
import { isPaymentMethod, PAYMENT_METHODS, paymentMethodLabel } from "../../payment-methods"

interface PaymentMethodSelectProps {
  /** The chosen method (there's always one). */
  value: PaymentMethod
  /** Called with the newly chosen method. */
  onChange: (value: PaymentMethod) => void
  /** Ties it to a visible <Label htmlFor>. */
  id?: string
  className?: string
  /** For a dropdown with no visible <Label>. */
  ariaLabel?: string
}

/**
 * The payment-method dropdown, used by both the Add dialog and the inline edit row. It always shows one of
 * the methods; `onChange` gets only a valid one (the Select reports plain strings, so each is checked first).
 */
export function PaymentMethodSelect({ value, onChange, id, className, ariaLabel }: PaymentMethodSelectProps) {
  return (
    <Select value={value} onValueChange={(next) => isPaymentMethod(next) && onChange(next)}>
      <SelectTrigger id={id} className={className} aria-label={ariaLabel}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {PAYMENT_METHODS.map((method) => (
          <SelectItem key={method} value={method}>
            {paymentMethodLabel(method)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
