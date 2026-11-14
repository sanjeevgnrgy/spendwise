// A shared component: the "couldn't refresh, so this may be out of date" line shown above data that's still on
// screen. Part of shared/. Used by the Dashboard and Expenses pages.

import { RefreshCw, TriangleAlert } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/shared/ui/button"

interface RefreshNoticeProps {
  /** Why the reload failed (messageOf the error). */
  message: string
  /** Retry was pressed. */
  onRetry: () => void
  /** A retry is in flight: the button waits and its icon spins. */
  retrying?: boolean
}

/**
 * Data is on screen, but reloading it just failed: keep showing it, and say it may be out of date, with Retry.
 * (Replacing good data with an error card because one refresh failed would be worse.)
 */
export function RefreshNotice({ message, onRetry, retrying = false }: RefreshNoticeProps) {
  const { t } = useTranslation()
  // <output> is announced politely by screen readers (its role is "status").
  return (
    <output className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground">
      <TriangleAlert className="size-4 shrink-0" />
      <span className="min-w-0 flex-1">{t("refreshNotice.stale", { message })}</span>
      <Button variant="ghost" size="sm" onClick={onRetry} disabled={retrying}>
        <RefreshCw className={retrying ? "animate-spin" : undefined} /> {t("retry.retry")}
      </Button>
    </output>
  )
}
