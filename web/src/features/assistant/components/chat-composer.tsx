// A component of the assistant feature: the message box at the bottom of the chat panel, with Send (or Stop
// while a run is in progress). It owns what's being typed, so a keystroke redraws only this box, not the
// conversation. Used by ChatPanel (chat-panel.tsx).

import { SendHorizontal, Square } from "lucide-react"
import { memo, useState, type FormEvent, type KeyboardEvent } from "react"

import { LIMITS } from "@/shared/api/contracts.gen"
import { Button } from "@/shared/ui/button"
import { Textarea } from "@/shared/ui/textarea"

interface ChatComposerProps {
  /** A run is in progress: typing still works, Enter does nothing (the text stays, to send later), Send is Stop. */
  sending: boolean
  /** Called with the trimmed text when the user sends a message. */
  onSend: (text: string) => void
  /** Called by Stop. */
  onStop: () => void
}

/**
 * The message box. Enter sends, Shift+Enter adds a new line; an empty (or all-space) message isn't sent, and
 * while a run is in progress nothing is sent: the text stays in the box until the run ends. Stop ends the run: the connection closes, and anything already
 * said or done stays. Memoised, so a streamed reply doesn't redraw it.
 */
export const ChatComposer = memo(function ChatComposer({ sending, onSend, onStop }: ChatComposerProps) {
  const [input, setInput] = useState("")

  function submit() {
    const text = input.trim()
    if (!text || sending) return
    setInput("")
    onSend(text)
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
    <form onSubmit={handleSubmit} className="flex shrink-0 items-end gap-2 border-t p-3">
      <Textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask or record an expense…"
        rows={2}
        maxLength={LIMITS.messageLength}
        className="max-h-40 min-h-0 resize-none"
        aria-label="Message"
      />
      {sending ? (
        <Button type="button" size="icon" variant="outline" aria-label="Stop" title="Stop" onClick={onStop}>
          <Square />
        </Button>
      ) : (
        <Button type="submit" size="icon" aria-label="Send" disabled={!input.trim()}>
          <SendHorizontal />
        </Button>
      )}
    </form>
  )
})
