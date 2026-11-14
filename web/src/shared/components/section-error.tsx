// A shared component: the error card that takes the place of a part that couldn't load or crashed. Part of shared/.
// Used by the pages (nothing loaded) and by app/ as the error boundaries' fallback (app-crashed.tsx, the layout).

import { RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"

interface SectionErrorProps {
  /** What couldn't be shown ("Couldn't load the dashboard"). */
  title: string
  /** Why (messageOf the error). */
  message: string
  /** Try again was pressed. */
  onRetry: () => void
  /** A retry is in flight: the button says so and waits. */
  retrying?: boolean
}

/**
 * A part of a page that couldn't load (or crashed): say what happened and offer to try again, instead of showing
 * misleading zeros or a blank page. It's an alert, so screen readers announce it at once.
 */
export function SectionError({ title, message, onRetry, retrying = false }: SectionErrorProps) {
  const { t } = useTranslation()
  return (
    <Card role="alert">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button variant="outline" onClick={onRetry} disabled={retrying}>
          <RefreshCw className={retrying ? "animate-spin" : undefined} />
          {retrying ? t("retry.tryingAgain") : t("retry.tryAgain")}
        </Button>
      </CardContent>
    </Card>
  )
}
