import { Wrench } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { ChatMessage } from "@/hooks/use-chat"
import { cn } from "@/lib/utils"

// One bubble: yours on the right, the assistant's on the left, with the tools it used underneath.
export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex flex-col gap-1.5", isUser ? "items-end" : "items-start")}>
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

      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="flex max-w-[85%] flex-wrap items-center gap-1 text-xs text-muted-foreground">
          <Wrench className="size-3" />
          {message.toolCalls.map((call, index) => (
            // A failed tool call shows in red: the assistant tried, the backend said no.
            <Badge key={index} variant={call.ok ? "secondary" : "destructive"}>
              {call.name.replaceAll("_", " ")}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}
