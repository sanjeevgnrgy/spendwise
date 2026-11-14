// The note the assistant feature's A2UI renderer draws in place of anything it won't or can't draw: an
// unknown catalog or component, a malformed property, a card over the limits, or a card that crashed.
// Used by every renderer in this folder.

import { useTexts } from "../i18n"
import type en from "../i18n/en"

/** Why something isn't drawn: a key of the "unsupported" texts, each a whole "Can't show …" sentence. */
export type UnsupportedReason = keyof typeof en.unsupported

interface UnsupportedProps {
  reason: UnsupportedReason
  /** The component's name as the server sent it, for "unknownComponent" (shown as text, never looked up). */
  component?: string
}

/**
 * What an unknown or broken part of an A2UI description becomes: a visible, harmless "Can't show …" note, in the
 * language on now.
 */
export function Unsupported({ reason, component }: UnsupportedProps) {
  const { t } = useTexts()
  return (
    <div className="rounded-md border border-dashed px-2 py-1 text-xs text-muted-foreground">
      {t(`unsupported.${reason}`, { component })}
    </div>
  )
}
