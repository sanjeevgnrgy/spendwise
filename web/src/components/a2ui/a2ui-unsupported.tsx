// What an unknown or broken part of an A2UI description becomes: a visible, harmless note.
export function Unsupported({ what }: { what: string }) {
  return (
    <div className="rounded-md border border-dashed px-2 py-1 text-xs text-muted-foreground">Can't show {what}</div>
  )
}
