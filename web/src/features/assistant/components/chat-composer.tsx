// A component of the assistant feature: the message box at the bottom of the chat panel, with a button to attach a
// receipt, and Send (or Stop while a run is in progress). It owns what's being typed and attached, so a keystroke
// redraws only this box, not the conversation. Used by ChatPanel (chat-panel.tsx).

import { SendHorizontal, Square } from "lucide-react"
import { memo, useState, type FormEvent, type KeyboardEvent } from "react"

import { LIMITS } from "@/shared/api/contracts.gen"
import { Button } from "@/shared/ui/button"
import { Textarea } from "@/shared/ui/textarea"

import { useTexts } from "../i18n"
import { AttachButton } from "./attach-button"
import { AttachedFile } from "./attached-file"

interface ChatComposerProps {
  /** A run is in progress: typing still works, Enter does nothing (the text stays, to send later), Send is Stop. */
  sending: boolean
  /** Called with the trimmed text, and the attached receipt if there is one, when the user sends. */
  onSend: (text: string, file?: File) => void
  /** Called by Stop. */
  onStop: () => void
}

/**
 * The message box. Enter sends, Shift+Enter adds a new line. A message needs text or an attached receipt (then the
 * text may be empty); while a run is in progress nothing is sent: what's typed and attached stays until it ends.
 * Stop ends the run: the connection closes, and anything already said or done stays. Memoised, so a streamed reply
 * doesn't redraw it; its own texts still follow a change of language (useTexts subscribes it).
 */
export const ChatComposer = memo(function ChatComposer({ sending, onSend, onStop }: ChatComposerProps) {
  const [input, setInput] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const { t } = useTexts()
  const ready = Boolean(input.trim() || file)

  function submit() {
    if (!ready || sending) return
    onSend(input.trim(), file ?? undefined)
    setInput("")
    setFile(null)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    submit()
  }

  // As in most chat apps. While an input method (e.g. for Hindi or Japanese) is composing, Enter picks the
  // suggested text instead, so it mustn't send.
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing) return
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex shrink-0 flex-col items-start gap-2 border-t p-3">
      {file && <AttachedFile name={file.name} onRemove={() => setFile(null)} />}
      <div className="flex w-full items-end gap-2">
        <AttachButton disabled={sending} onAttach={setFile} />
        <Textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("composer.placeholder")}
          rows={2}
          maxLength={LIMITS.messageLength}
          className="max-h-40 min-h-0 resize-none"
          aria-label={t("composer.label")}
        />
        {sending ? (
          <Button
            type="button"
            size="icon"
            variant="outline"
            aria-label={t("composer.stop")}
            title={t("composer.stop")}
            onClick={onStop}
          >
            <Square />
          </Button>
        ) : (
          <Button type="submit" size="icon" aria-label={t("composer.send")} disabled={!ready}>
            <SendHorizontal />
          </Button>
        )}
      </div>
    </form>
  )
})
