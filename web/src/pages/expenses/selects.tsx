import { PAYMENT_METHODS, type Category, type PaymentMethod } from "@/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { paymentMethodLabel } from "@/lib/format"

// Two small dropdowns used by both the Add dialog and the inline edit row, so they're written once.

interface CategorySelectProps {
  categories: Category[]
  value: string // the category id as text ("" = nothing chosen yet), because <Select> works with strings
  onChange: (value: string) => void
  id?: string
  className?: string
}

export function CategorySelect({ categories, value, onChange, id, className }: CategorySelectProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className={className}>
        <SelectValue placeholder="Choose a category" />
      </SelectTrigger>
      <SelectContent>
        {categories.map((category) => (
          <SelectItem key={category.id} value={String(category.id)}>
            {category.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

interface PaymentMethodSelectProps {
  value: PaymentMethod
  onChange: (value: PaymentMethod) => void
  id?: string
  className?: string
}

export function PaymentMethodSelect({ value, onChange, id, className }: PaymentMethodSelectProps) {
  return (
    // The list only contains valid methods, so the cast back to PaymentMethod is safe.
    <Select value={value} onValueChange={(next) => onChange(next as PaymentMethod)}>
      <SelectTrigger id={id} className={className}>
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
