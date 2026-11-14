// A component of the assistant feature: the conversation's scrolling area in the chat panel. Suggestions while
// it's empty, one bubble per message, "Thinking…" while the assistant has nothing to show yet, and auto-scroll
// to the newest content. Used by ChatPanel (chat-panel.tsx).

import { Loader2 } from "lucide-react"
import { useEffect, useRef } from "react"

import { Button } from "@/shared/ui/button"
import { ScrollArea } from "@/shared/ui/scroll-area"

import type { A2uiRenderContext } from "../a2ui/protocol"
import type { ChatMessage } from "../model/chat-types"
import { ChatMessageBubble } from "./chat-message"

const SUGGESTIONS = [
  "How much did I spend on food this month?",
  "Add 250 for lunch at Subway today, paid by UPI",
  "What were my 3 biggest expenses this month?",
]

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
  if (last?.role !== "assistant") return true
  return !last.text && !last.tools?.some((tool) => tool.status === "running")
}

// What an empty conversation shows: a short hint and a few messages to try.
function Suggestions({ sending, onSuggestion }: Pick<ChatTranscriptProps, "sending" | "onSuggestion">) {
  return (
    <div className="flex flex-col gap-2 py-4 text-sm text-muted-foreground">
      <p>Ask about your spending, or record an expense in plain words. Try:</p>
      {SUGGESTIONS.map((suggestion) => (
        <Button
          key={suggestion}
          variant="outline"
          size="sm"
          className="h-auto justify-start py-1.5 text-left whitespace-normal"
          onClick={() => onSuggestion(suggestion)}
          disabled={sending}
        >
          {suggestion}
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

  // Keep the newest content in view: a new message, more reply text, a new chip or card. Not on every
  // keystroke in a form (that changes the messages too), which would yank the field you're typing in
  // out of view. Scrolling is a change outside React's own output, which is what an effect is for.
  const last = messages.at(-1)
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" })
  }, [messages.length, last?.text, last?.tools?.length, last?.surfaces?.length, sending])

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-col gap-3 p-3">
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
            <Loader2 className="size-4 animate-spin" /> Thinking…
          </div>
        )}
        <div ref={endRef} />
      </div>
    </ScrollArea>
  )
}
