// The "New token" button and its dialog: first the form, then, once the token is made, the token itself, shown this
// once. Part of the account feature (components/tokens/). Used by tokens-card.tsx.

import { Plus } from "lucide-react"
import { useState, type FormEvent } from "react"
import { toast } from "sonner"

import { messageOf } from "@/shared/lib/errors"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogTrigger } from "@/shared/ui/dialog"

import type { NewAccessToken } from "../../api"
import { useTexts } from "../../i18n"
import { useCreateAccessToken } from "../../queries"
import { BLANK_TOKEN } from "../../token-form"
import { TokenCreated } from "./token-created"
import { TokenFields } from "./token-fields"

/**
 * Makes a token. The token is kept only in this dialog's state while it's open: closing the dialog forgets it (and
 * the request's answer), so it can't be read again afterwards, by anyone. While it's on screen a click outside
 * doesn't close the dialog, so it isn't lost by accident before it's copied.
 */
export function CreateTokenDialog() {
  const { t } = useTexts()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<NewAccessToken>(BLANK_TOKEN)
  const [token, setToken] = useState<string | null>(null)
  const create = useCreateAccessToken()

  function handleOpenChange(next: boolean) {
    setOpen(next)
    if (next) return
    setDraft(BLANK_TOKEN)
    setToken(null)
    create.reset()
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault() // stop the browser's default form submit, which would reload the page
    create.mutate(
      { ...draft, name: draft.name.trim() },
      // e.g. "You can have at most 10 access tokens", straight from the backend's rules. The dialog stays open.
      { onSuccess: (created) => setToken(created.token), onError: (error) => toast.error(messageOf(error)) },
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus /> {t("tokens.create")}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md" onInteractOutside={(event) => token && event.preventDefault()}>
        {token ? (
          <TokenCreated token={token} onDone={() => handleOpenChange(false)} />
        ) : (
          <TokenFields draft={draft} onChange={setDraft} onSubmit={handleSubmit} creating={create.isPending} />
        )}
      </DialogContent>
    </Dialog>
  )
}
