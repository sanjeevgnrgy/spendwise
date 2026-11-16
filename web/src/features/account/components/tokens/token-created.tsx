// What the "new access token" dialog shows once the token is made: the token itself, this once, with Copy. Part of the
// account feature (components/tokens/). Used by create-token-dialog.tsx, which forgets the token when the dialog
// closes. The token is never written to browser storage or a log: it lives in this dialog's memory only.

import { Copy } from "lucide-react"
import { toast } from "sonner"

import { LabeledField } from "@/shared/components/labeled-field"
import { Button } from "@/shared/ui/button"
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"

import { useTexts } from "../../i18n"

interface TokenCreatedProps {
  /** The new token, as the server sent it. */
  token: string
  /** Done was pressed: close the dialog. */
  onDone: () => void
}

/** The token in a read-only box (focusing it selects it all), a Copy button, and Done. */
export function TokenCreated({ token, onDone }: TokenCreatedProps) {
  const { t } = useTexts()

  // The clipboard can refuse (an insecure page, a denied permission): then the person copies it by hand.
  async function copy() {
    try {
      await navigator.clipboard.writeText(token)
      toast.success(t("newToken.copied"))
    } catch {
      toast.error(t("newToken.copyFailed"))
    }
  }

  return (
    <div className="grid gap-4">
      <DialogHeader>
        <DialogTitle>{t("newToken.createdTitle")}</DialogTitle>
        <DialogDescription>{t("newToken.createdDescription")}</DialogDescription>
      </DialogHeader>
      <LabeledField id="token-value" label={t("newToken.token")}>
        <div className="flex gap-2">
          <Input
            id="token-value"
            readOnly
            autoComplete="off"
            spellCheck={false}
            className="font-mono"
            value={token}
            onFocus={(event) => event.target.select()}
          />
          <Button type="button" variant="outline" onClick={() => void copy()}>
            <Copy /> {t("newToken.copy")}
          </Button>
        </div>
      </LabeledField>
      <DialogFooter>
        <Button type="button" onClick={onDone}>
          {t("newToken.done")}
        </Button>
      </DialogFooter>
    </div>
  )
}
