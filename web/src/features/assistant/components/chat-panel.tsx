import { Bot, Loader2, SendHorizontal, Square, SquarePen, X } from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"

import { LIMITS } from "@/shared/api/contracts.gen"
import { Button } from "@/shared/ui/button"
import { ScrollArea } from "@/shared/ui/scroll-area"
import { Textarea } from "@/shared/ui/textarea"

import { useAssistant } from "../model/assistant-context"
import type { ChatMessage } from "../model/use-chat"
import { ChatMessageBubble } from "./chat-message"

const SUGGESTIONS = [
  "How much did I spend on food this month?",
  "Add 250 for lunch at Subway today, paid by UPI",
  "What were my 3 biggest expenses this month?",
]

// True while the assistant is working with nothing to show yet: before its first event, or after its
// tools have finished and before the answer's text starts (the model is deciding what to say).
function isWaiting(last: ChatMessage | undefined): boolean {
  if (last?.role !== "assistant") return true
  return !last.text && !last.tools?.some((tool) => tool.status === "running")
}

export function ChatPanel({ onClose }: { onClose: () => void }) {
  const chat = useAssistant()
  const [input, setInput] = useState("")
  const endRef = useRef<HTMLDivElement>(null)

  // Keep the newest content in view: a new message, more reply text, a new chip or card. Not on every
  // keystroke in a form (that changes the messages too), which would yank the field you're typing in
  // out of view. Scrolling is a change outside React's own output, which is what an effect is for.
  const last = chat.messages.at(-1)
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" })
  }, [chat.messages.length, last?.text, last?.tools?.length, last?.surfaces?.length, chat.sending])

  function submit() {
    const text = input.trim()
    if (!text || chat.sending) return
    setInput("")
    chat.send(text)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    submit()
  }

  // Enter sends, Shift+Enter adds a new line (as in most chat apps). While an input method (e.g. for
  // Hindi or Japanese) is composing, Enter picks the suggested text instead, so it mustn't send.
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing) return
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
        <Bot className="size-4" />
        <span className="font-medium">Assistant</span>
        <div className="ml-auto flex gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="New conversation"
            title="New conversation"
            onClick={chat.reset}
            disabled={chat.sending || chat.messages.length === 0}
          >
            <SquarePen />
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label="Close assistant" onClick={onClose}>
            <X />
          </Button>
        </div>
      </div>

      {/* min-h-0 lets this area shrink and scroll instead of pushing the input box off screen. */}
      <ScrollArea className="min-h-0 flex-1">
        {/* role="log": screen readers announce new messages and the streamed reply as they arrive. */}
        <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-col gap-3 p-3">
          {chat.messages.length === 0 && (
            <div className="flex flex-col gap-2 py-4 text-sm text-muted-foreground">
              <p>Ask about your spending, or record an expense in plain words. Try:</p>
              {SUGGESTIONS.map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  className="h-auto justify-start py-1.5 text-left whitespace-normal"
                  onClick={() => chat.send(suggestion)}
                  disabled={chat.sending}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          )}

          {chat.messages.map((message) => (
            <ChatMessageBubble
              key={message.id}
              message={message}
              formsLocked={chat.sending}
              onFormChange={chat.setFormValue}
              onFormSubmit={chat.submitForm}
            />
          ))}

          {/* Only while nothing else shows progress: not while a tool chip spins or text is arriving. */}
          {chat.sending && isWaiting(last) && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Thinking…
            </div>
          )}
          <div ref={endRef} />
        </div>
      </ScrollArea>

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
        {chat.sending ? (
          // Stop ends the run: the connection closes, and anything already said or done stays.
          <Button type="button" size="icon" variant="outline" aria-label="Stop" title="Stop" onClick={chat.stop}>
            <Square />
          </Button>
        ) : (
          <Button type="submit" size="icon" aria-label="Send" disabled={!input.trim()}>
            <SendHorizontal />
          </Button>
        )}
      </form>
    </div>
  )
}
