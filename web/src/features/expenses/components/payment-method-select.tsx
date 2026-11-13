import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

import type { PaymentMethod } from "../api"
import { isPaymentMethod, PAYMENT_METHODS, paymentMethodLabel } from "../payment-methods"

interface PaymentMethodSelectProps {
  value: PaymentMethod
  onChange: (value: PaymentMethod) => void
  id?: string
  className?: string
  ariaLabel?: string // for a dropdown with no visible <Label>
}

// The payment-method dropdown, used by both the Add dialog and the inline edit row.
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
