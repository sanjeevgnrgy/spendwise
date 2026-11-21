// A component of the assistant feature: the conversation's scrolling area in the chat panel. Suggestions while
// it's empty, one bubble per message, "Thinking…" while the assistant has nothing to show yet, and auto-scroll
// to the newest content. Used by ChatPanel (chat-panel.tsx).

import { Loader2 } from "lucide-react"
import { useEffect, useRef } from "react"

import { Button } from "@/shared/ui/button"
import { ScrollArea } from "@/shared/ui/scroll-area"

import type { A2uiRenderContext } from "../a2ui/protocol"
import { useTexts } from "../i18n"
import type en from "../i18n/en"
import { MESSAGE_ROLES, TOOL_STATUSES, type ChatMessage } from "../model/chat-types"
import { ChatMessageBubble } from "./chat-message"

// The messages to try, in order: keys of the "suggestions" texts, looked up when drawn, so each one is shown (and
// sent) in the language on now. Nothing parses them: a suggestion is sent like anything typed.
const SUGGESTIONS: readonly (keyof typeof en.suggestions)[] = ["foodThisMonth", "addLunch", "biggestExpenses"]

interface ChatTranscriptProps {
  messages: ChatMessage[]
  /** A run is in progress: suggestions are disabled, forms locked, and "Thinking…" may show. */
  sending: boolean
  /** Called with a suggestion's text when it's clicked: it's sent as a message. */
  onSuggestion: (text: string) => void
  onFormChange: A2uiRenderContext["onChange"]
  onFormSubmit: A2uiRenderContext["onAction"]
}

// True while the assistant is working with nothing to show yet: before its first event, or after its
// tools have finished and before the answer's text starts (the model is deciding what to say).
function isWaiting(last: ChatMessage | undefined): boolean {
  if (last?.role !== MESSAGE_ROLES.assistant) return true
  return !last.text && !last.tools?.some((tool) => tool.status === TOOL_STATUSES.running)
}

// What an empty conversation shows: a short hint and a few messages to try.
function Suggestions({ sending, onSuggestion }: Pick<ChatTranscriptProps, "sending" | "onSuggestion">) {
  const { t } = useTexts()
  return (
    <div className="flex flex-col gap-2 py-4 text-sm text-muted-foreground">
      <p>{t("transcript.hint")}</p>
      {SUGGESTIONS.map((suggestion) => (
        <Button
          key={suggestion}
          variant="outline"
          size="sm"
          className="h-auto justify-start py-1.5 text-left whitespace-normal"
          onClick={() => onSuggestion(t(`suggestions.${suggestion}`))}
          disabled={sending}
        >
          {t(`suggestions.${suggestion}`)}
        </Button>
      ))}
    </div>
  )
}

/**
 * The conversation. The area is a `role="log"` polite live region, so screen readers announce new messages and
 * the streamed reply as they arrive; its min-h-0 lets it shrink and scroll instead of pushing the message box
 * off screen. "Thinking…" shows only while nothing else shows progress: not while a chip spins or text arrives.
 */
export function ChatTranscript({ messages, sending, onSuggestion, onFormChange, onFormSubmit }: ChatTranscriptProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const { t } = useTexts()

  // Keep the newest content in view: a new message, more reply text, a new chip or card. Not on every
  // keystroke in a form (that changes the messages too), which would yank the field you're typing in
  // out of view. Scrolling is a change outside React's own output, which is what an effect is for.
  const last = messages.at(-1)
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" })
  }, [messages.length, last?.text, last?.tools?.length, last?.surfaces?.length, sending])

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div role="log" aria-live="polite" aria-label={t("transcript.label")} className="flex flex-col gap-3 p-3">
        {messages.length === 0 && <Suggestions sending={sending} onSuggestion={onSuggestion} />}

        {messages.map((message) => (
          <ChatMessageBubble
            key={message.id}
            message={message}
            formsLocked={sending}
            onFormChange={onFormChange}
            onFormSubmit={onFormSubmit}
          />
        ))}

        {sending && isWaiting(last) && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> {t("transcript.thinking")}
          </div>
        )}
        <div ref={endRef} />
      </div>
    </ScrollArea>
  )
}
