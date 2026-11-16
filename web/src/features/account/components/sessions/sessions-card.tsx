// The Settings page's "Where you're signed in" card: every browser signed in to the account, and "Sign out everywhere
// else". Part of the account feature (components/sessions/). Used by settings-page.tsx.

import { useState } from "react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"
import { Button } from "@/shared/ui/button"

import { useTexts } from "../../i18n"
import { useSessions, useSignOutOtherSessions } from "../../queries"
import { ConfirmDialog } from "../confirm-dialog"
import { SectionCard } from "../section-card"
import { SessionRow } from "./session-row"

/** The list of the person's live sessions, this browser marked, with a way to end all the others at once. */
export function SessionsCard() {
  const { t } = useTexts()
  const sessions = useSessions()
  return (
    <SectionCard
      title={t("sessions.title")}
      description={t("sessions.description")}
      query={sessions}
      loadFailed={t("sessions.loadFailed")}
    >
      {(items) => (
        <>
          <ul className="divide-y">
            {items.map((session) => (
              <SessionRow key={session.id} session={session} />
            ))}
          </ul>
          <SignOutOthers disabled={items.length < 2} />
        </>
      )}
    </SectionCard>
  )
}

// "Sign out everywhere else": asks first, then ends every session but this browser's. Disabled when this is the only
// one. For the case a person fears someone else has their session: it works whatever the other browser is doing.
function SignOutOthers({ disabled }: { disabled: boolean }) {
  const { t } = useTexts()
  const [confirming, setConfirming] = useState(false)
  const signOutOthers = useSignOutOtherSessions()

  function handleConfirm() {
    signOutOthers.mutate(undefined, {
      onSuccess: () => toast.success(t("sessions.othersSignedOut")),
      onError: (error) => toast.error(messageOf(error)),
    })
  }

  return (
    <div>
      <Button
        variant="outline"
        size="sm"
        disabled={disabled || signOutOthers.isPending}
        onClick={() => setConfirming(true)}
      >
        {t("sessions.signOutOthers")}
      </Button>
      <ConfirmDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={t("sessions.signOutOthersTitle")}
        description={t("sessions.signOutOthersDescription")}
        confirmLabel={t("sessions.signOutOthers")}
        onConfirm={handleConfirm}
      />
    </div>
  )
}
