import { Bot, Loader2, SendHorizontal, SquarePen, X } from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react"

import { ChatMessageBubble } from "@/components/chat/chat-message"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import type { ChatState } from "@/hooks/use-chat"

const SUGGESTIONS = [
  "How much did I spend on food this month?",
  "Add 250 for lunch at Subway today, paid by UPI",
  "What were my 3 biggest expenses this month?",
]

interface ChatPanelProps {
  chat: ChatState // the conversation lives in the layout, so it survives closing this panel
  onClose: () => void
}

export function ChatPanel({ chat, onClose }: ChatPanelProps) {
  const [input, setInput] = useState("")
  const endRef = useRef<HTMLDivElement>(null)

  // Keep the newest message in view. Scrolling is a change outside React's own output,
  // which is exactly what an effect is for.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" })
  }, [chat.messages, chat.sending])

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

  // Enter sends, Shift+Enter adds a new line (as in most chat apps).
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
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
        <div className="flex flex-col gap-3 p-3">
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
            <ChatMessageBubble key={message.id} message={message} />
          ))}

          {chat.sending && (
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
          maxLength={2000}
          className="max-h-40 min-h-0 resize-none"
          aria-label="Message"
        />
        <Button type="submit" size="icon" aria-label="Send" disabled={!input.trim() || chat.sending}>
          <SendHorizontal />
        </Button>
      </form>
    </div>
  )
}
