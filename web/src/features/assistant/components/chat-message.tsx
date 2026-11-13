import { cn } from "@/shared/lib/utils"

import { A2uiSurfaceView } from "../a2ui/a2ui-surface"
import type { A2uiRenderContext } from "../a2ui/protocol"
import type { ChatMessage } from "../model/use-chat"
import { ToolChip } from "./tool-chip"

interface ChatMessageBubbleProps {
  message: ChatMessage
  formsLocked?: boolean // while a run is in progress, forms can't be changed or sent
  onFormChange?: A2uiRenderContext["onChange"]
  onFormSubmit?: A2uiRenderContext["onAction"]
}

// One bubble: yours on the right, the assistant's on the left. The assistant's tool activity and
// any cards or forms are shown above its text, because the tools run before it answers.
export function ChatMessageBubble({ message, formsLocked, onFormChange, onFormSubmit }: ChatMessageBubbleProps) {
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

      {/* Cards come with a tool's result, so they sit between the chips and the reply text. */}
      {message.surfaces && message.surfaces.length > 0 && (
        <div className="flex w-full max-w-[85%] flex-col gap-2">
          {message.surfaces.map((surface) => (
            <A2uiSurfaceView
              key={surface.id}
              surface={surface}
              locked={formsLocked}
              onChange={onFormChange}
              onAction={onFormSubmit}
            />
          ))}
        </div>
      )}

      {/* An assistant reply can be tools only for a moment, before its text arrives. */}
      {(isUser || message.text) && (
        <div
          className={cn(
            // whitespace-pre-wrap: keep the line breaks in the assistant's text.
            "max-w-[85%] rounded-lg px-3 py-2 text-sm wrap-break-word whitespace-pre-wrap",
            isUser && "bg-primary text-primary-foreground",
            !isUser && !message.status && "bg-muted",
            message.status === "failed" && "border border-destructive/40 bg-destructive/10 text-destructive",
            message.status === "stopped" && "border text-muted-foreground",
          )}
        >
          {message.text}
        </div>
      )}
    </div>
  )
}
