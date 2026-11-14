// A component of the assistant feature: an attached receipt as a small chip, its file name and, in the composer, a
// button that removes it. Used by ChatComposer (before sending) and ChatMessageBubble (in a sent message).

import { Paperclip, X } from "lucide-react"

import { cn } from "@/shared/lib/utils"

import { useTexts } from "../i18n"

interface AttachedFileProps {
  /** The file's name: the user's own data, shown as it is. */
  name: string
  /** In the composer: removes the attachment before it's sent. Left out in a sent message. */
  onRemove?: () => void
}

/** One attached file. Screen readers hear "Attached: <name>"; a long name is cut, with the whole of it on hover. */
export function AttachedFile({ name, onRemove }: AttachedFileProps) {
  const { t } = useTexts()
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1 rounded-md border px-2 py-1 text-xs",
        "bg-background text-foreground",
      )}
    >
      <Paperclip className="size-3 shrink-0" aria-hidden="true" />
      <span className="truncate" title={name}>
        <span className="sr-only">{t("transcript.attached", { name })}</span>
        <span aria-hidden="true">{name}</span>
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={t("composer.removeAttachment", { name })}
          className={cn(
            "shrink-0 rounded-sm text-muted-foreground hover:text-foreground",
            "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
          )}
        >
          <X className="size-3" />
        </button>
      )}
    </span>
  )
}
