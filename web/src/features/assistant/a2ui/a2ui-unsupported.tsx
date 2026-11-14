// The note the assistant feature's A2UI renderer draws in place of anything it won't or can't draw: an
// unknown catalog or component, a malformed property, a card over the limits, or a card that crashed.
// Used by every renderer in this folder.

/** What an unknown or broken part of an A2UI description becomes: a visible, harmless "Can't show …" note. */
export function Unsupported({ what }: { what: string }) {
  return (
    <div className="rounded-md border border-dashed px-2 py-1 text-xs text-muted-foreground">Can't show {what}</div>
  )
}
