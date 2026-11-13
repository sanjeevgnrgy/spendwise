import { ToolChip } from "@/components/chat/tool-chip"
import type { ChatMessage } from "@/hooks/use-chat"
import { cn } from "@/lib/utils"

// One bubble: yours on the right, the assistant's on the left. The assistant's tool activity is
// shown above its text, because the tools run before it answers.
export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex flex-col gap-1.5", isUser ? "items-end" : "items-start")}>
      {message.tools && message.tools.length > 0 && (
        // aria-live: screen readers announce the chips as they change ("Expense saved").
        <div className="flex max-w-[85%] flex-wrap gap-1" aria-live="polite">
          {message.tools.map((tool) => (
            <ToolChip key={tool.id} tool={tool} />
          ))}
        </div>
      )}

      {/* An assistant reply can be tools only for a moment, before its text arrives. */}
      {(isUser || message.text) && (
        <div
          className={cn(
            // whitespace-pre-wrap: keep the line breaks in the assistant's text.
            "max-w-[85%] rounded-lg px-3 py-2 text-sm break-words whitespace-pre-wrap",
            isUser && "bg-primary text-primary-foreground",
            !isUser && !message.failed && "bg-muted",
            message.failed && "border border-destructive/40 bg-destructive/10 text-destructive",
          )}
        >
          {message.text}
        </div>
      )}
    </div>
  )
}
