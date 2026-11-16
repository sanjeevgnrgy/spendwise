// The "new access token" form: a name and how long the token should work. Part of the account feature
// (components/tokens/). Used by create-token-dialog.tsx, which owns the draft and sends it.

import type { FormEvent } from "react"

import { ACCOUNT } from "@/shared/api/contracts.gen"
import { LabeledField } from "@/shared/components/labeled-field"
import { Button } from "@/shared/ui/button"
import { DialogClose, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

import type { NewAccessToken } from "../../api"
import { useTexts } from "../../i18n"
import { isComplete, isTokenLifetime, TOKEN_LIFETIMES } from "../../token-form"

interface TokenFieldsProps {
  /** The form's values so far. */
  draft: NewAccessToken
  /** Called with the whole draft whenever a field changes. */
  onChange: (draft: NewAccessToken) => void
  /** Create was pressed (or Enter in the name box). */
  onSubmit: (event: FormEvent) => void
  /** The request is running: Create waits. */
  creating: boolean
}

/**
 * The form. The name is capped at the server's limit as it's typed, and the lifetimes are the server's own list, so
 * what can be sent is what the server accepts; the server still checks both.
 */
export function TokenFields({ draft, onChange, onSubmit, creating }: TokenFieldsProps) {
  const { t } = useTexts()
  // The Select reports plain text: only a lifetime on offer is taken.
  function setLifetime(value: string) {
    const days = Number(value)
    if (isTokenLifetime(days)) onChange({ ...draft, lifetime_days: days })
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-4">
      <DialogHeader>
        <DialogTitle>{t("newToken.title")}</DialogTitle>
        <DialogDescription>{t("newToken.description")}</DialogDescription>
      </DialogHeader>
      <LabeledField id="token-name" label={t("newToken.name")}>
        <Input
          id="token-name"
          autoComplete="off"
          maxLength={ACCOUNT.tokenNameLength}
          placeholder={t("newToken.nameExample")}
          value={draft.name}
          onChange={(event) => onChange({ ...draft, name: event.target.value })}
        />
      </LabeledField>
      <LabeledField id="token-lifetime" label={t("newToken.lifetime")}>
        <Select value={String(draft.lifetime_days)} onValueChange={setLifetime}>
          <SelectTrigger id="token-lifetime">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TOKEN_LIFETIMES.map((days) => (
              <SelectItem key={days} value={String(days)}>
                {t("newToken.days", { count: days })}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </LabeledField>
      <DialogFooter>
        <DialogClose asChild>
          <Button type="button" variant="outline">
            {t("actions.cancel")}
          </Button>
        </DialogClose>
        <Button type="submit" disabled={!isComplete(draft) || creating}>
          {creating ? t("newToken.creating") : t("newToken.create")}
        </Button>
      </DialogFooter>
    </form>
  )
}
