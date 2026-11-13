import { RefreshCw, TriangleAlert } from "lucide-react"

import { Button } from "@/shared/ui/button"

interface RefreshNoticeProps {
  message: string
  onRetry: () => void
  retrying?: boolean
}

// Data is on screen, but reloading it just failed: keep showing it, and say it may be out of date.
// (Replacing good data with an error card because one refresh failed would be worse.)
export function RefreshNotice({ message, onRetry, retrying = false }: RefreshNoticeProps) {
  return (
    // <output> is announced politely by screen readers (its role is "status").
    <output className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground">
      <TriangleAlert className="size-4 shrink-0" />
      <span className="min-w-0 flex-1">Couldn't refresh, so this may be out of date: {message}</span>
      <Button variant="ghost" size="sm" onClick={onRetry} disabled={retrying}>
        <RefreshCw className={retrying ? "animate-spin" : undefined} /> Retry
      </Button>
    </output>
  )
}
