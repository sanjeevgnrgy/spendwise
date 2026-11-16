// One form field: a visible label above its control. Part of shared/components (it knows no feature). Used by the
// expenses feature's Add dialog and filters bar and the account feature's token form, which each lay out several.

import type { ReactNode } from "react"

import { Label } from "@/shared/ui/label"

interface LabeledFieldProps {
  /** The control's id: the label points at it (htmlFor), so clicking the label focuses the control. */
  id: string
  /** The label's text. */
  label: string
  /** The control itself, which must carry the same `id`. */
  children: ReactNode
}

/**
 * A label and its control, stacked with a small gap. The label is tied to the control by `id`, so screen readers
 * announce it as the control's name; the caller gives the control that id (this component can't set it).
 */
export function LabeledField({ id, label, children }: LabeledFieldProps) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
    </div>
  )
}
