// A component of the assistant feature: the composer's paperclip button, which opens the file picker for a receipt
// and refuses at once a file the server would refuse (too large, not a photo or PDF). Used by ChatComposer
// (chat-composer.tsx).

import { Paperclip } from "lucide-react"
import { useRef, type ChangeEvent } from "react"
import { toast } from "sonner"

import { Button } from "@/shared/ui/button"

import { useTexts } from "../i18n"
import { attachmentProblem, MAX_RECEIPT_MB, RECEIPT_ACCEPT } from "../model/attachments"

interface AttachButtonProps {
  /** A run is in progress: no file can be chosen. */
  disabled: boolean
  /** Called with a chosen file that may be attached. */
  onAttach: (file: File) => void
}

/**
 * The attach button and the file input it opens (hidden: the button is what people see and focus). A file that
 * can't be a receipt is explained in a toast and not attached; the server still checks the file's own bytes.
 */
export function AttachButton({ disabled, onAttach }: AttachButtonProps) {
  const { t } = useTexts()
  const picker = useRef<HTMLInputElement>(null)

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    // Cleared, so choosing the same file again (after removing it) still counts as a change.
    event.target.value = ""
    if (!file) return
    const problem = attachmentProblem(file)
    if (problem) {
      toast.error(t(`composer.${problem}`, { name: file.name, max: MAX_RECEIPT_MB }))
      return
    }
    onAttach(file)
  }

  return (
    <>
      <input
        ref={picker}
        type="file"
        accept={RECEIPT_ACCEPT}
        hidden
        aria-label={t("composer.attach")}
        onChange={handleChange}
      />
      <Button
        type="button"
        size="icon"
        variant="ghost"
        aria-label={t("composer.attach")}
        title={t("composer.attach")}
        disabled={disabled}
        onClick={() => picker.current?.click()}
      >
        <Paperclip />
      </Button>
    </>
  )
}
