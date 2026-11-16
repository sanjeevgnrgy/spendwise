// One row of "Access tokens": a token's name, its last characters, its dates, and Revoke. Part of the account feature
// (components/tokens/). Used by tokens-card.tsx. The token itself is never here: the server only ever sent it once.

import { KeyRound } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"
import { formatDateTime } from "@/shared/lib/format"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import type { AccessToken } from "../../api"
import { useTexts } from "../../i18n"
import { useRevokeAccessToken } from "../../queries"
import { ConfirmDialog } from "../confirm-dialog"

/**
 * The token, marked if it has expired (the server says so: it no longer works, and can be removed). Revoke asks
 * first: apps using the token stop working at once, and it can't be brought back.
 */
export function TokenRow({ token }: { token: AccessToken }) {
  const { t } = useTexts()
  const revoke = useRevokeAccessToken()
  const [confirming, setConfirming] = useState(false)
  const dates = { created: formatDateTime(token.created_at), expires: formatDateTime(token.expires_at) }

  function handleRevoke() {
    revoke.mutate(token.id, {
      onSuccess: () => toast.success(t("tokens.revoked")),
      onError: (error) => toast.error(messageOf(error)),
    })
  }

  return (
    <li className="flex flex-wrap items-center gap-3 py-3">
      <KeyRound aria-hidden className="size-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1 text-sm text-muted-foreground">
        <p className="flex flex-wrap items-center gap-2 text-base font-medium text-foreground">
          <span className="truncate">{token.name}</span>
          {token.expired && <Badge variant="destructive">{t("tokens.expired")}</Badge>}
        </p>
        <p>{t("tokens.endsWith", { hint: token.hint })}</p>
        <p>{t("tokens.dates", dates)}</p>
        <p>
          {token.last_used_at
            ? t("tokens.lastUsed", { when: formatDateTime(token.last_used_at) })
            : t("tokens.neverUsed")}
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={revoke.isPending}
        aria-label={t("tokens.revokeLabel", { name: token.name })}
        onClick={() => setConfirming(true)}
      >
        {t("tokens.revoke")}
      </Button>
      <ConfirmDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        title={t("tokens.revokeTitle")}
        description={t("tokens.revokeDescription", { name: token.name })}
        confirmLabel={t("tokens.revoke")}
        onConfirm={handleRevoke}
      />
    </li>
  )
}
