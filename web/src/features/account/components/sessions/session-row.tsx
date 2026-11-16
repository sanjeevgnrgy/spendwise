// One row of "Where you're signed in": a browser, when it signed in and was last active, and Sign out for any browser
// but this one. Part of the account feature (components/sessions/). Used by sessions-card.tsx.

import { Monitor } from "lucide-react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"
import { formatDateTime } from "@/shared/lib/format"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import type { Session } from "../../api"
import { deviceOf } from "../../device-name"
import { useTexts } from "../../i18n"
import { useSignOutSession } from "../../queries"

/**
 * The session's browser ("Edge on Windows", or whichever half is known), marked if it's this one. Signing another
 * browser out ends its session on the server at once; this browser signs out through the top bar's menu, which also
 * signs out at the identity provider.
 */
export function SessionRow({ session }: { session: Session }) {
  const { t } = useTexts()
  const signOut = useSignOutSession()
  const { browser, system } = deviceOf(session.user_agent)
  const device =
    browser && system ? t("sessions.deviceOn", { browser, system }) : (browser ?? system ?? t("sessions.unknownDevice"))
  const signedIn = formatDateTime(session.created_at)

  function handleSignOut() {
    signOut.mutate(session.id, {
      onSuccess: () => toast.success(t("sessions.signedOut")),
      onError: (error) => toast.error(messageOf(error)),
    })
  }

  return (
    <li className="flex flex-wrap items-center gap-3 py-3">
      <Monitor aria-hidden className="size-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="flex flex-wrap items-center gap-2 font-medium">
          {device}
          {session.current && <Badge variant="secondary">{t("sessions.thisBrowser")}</Badge>}
        </p>
        <p className="text-sm text-muted-foreground">
          {t("sessions.times", { signedIn, lastActive: formatDateTime(session.last_active_at) })}
        </p>
      </div>
      {!session.current && (
        <Button
          variant="outline"
          size="sm"
          disabled={signOut.isPending}
          aria-label={t("sessions.signOutLabel", { device, signedIn })}
          onClick={handleSignOut}
        >
          {t("sessions.signOut")}
        </Button>
      )}
    </li>
  )
}
