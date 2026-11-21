// A component of the assistant feature: one message bubble in the conversation, with the assistant's tool chips
// and A2UI cards. Used by ChatTranscript (chat-transcript.tsx), once per message.

import { memo } from "react"

import { cn } from "@/shared/lib/utils"

import { A2uiSurfaceView } from "../a2ui/a2ui-surface"
import type { A2uiRenderContext } from "../a2ui/protocol"
import { MESSAGE_ROLES, type ChatMessage, type MessageStatus } from "../model/chat-types"
import { AttachedFile } from "./attached-file"
import { ToolChip } from "./tool-chip"

// How a bubble looks: the person's, the assistant's, and an assistant reply that failed or was stopped.
const USER_BUBBLE = "bg-primary text-primary-foreground"
const ASSISTANT_BUBBLE = "bg-muted"
const ENDED_BUBBLES: Readonly<Record<MessageStatus, string>> = {
  failed: "border border-destructive/40 bg-destructive/10 text-destructive",
  stopped: "border text-muted-foreground",
}

/** The bubble's colours for a message: by who wrote it, and how an assistant reply ended. */
function bubbleStyle(message: ChatMessage): string {
  if (message.role === MESSAGE_ROLES.user) return USER_BUBBLE
  return message.status ? ENDED_BUBBLES[message.status] : ASSISTANT_BUBBLE
}

interface ChatMessageBubbleProps {
  message: ChatMessage
  /** While a run is in progress, forms can't be changed or sent. */
  formsLocked?: boolean
  onFormChange?: A2uiRenderContext["onChange"]
  onFormSubmit?: A2uiRenderContext["onAction"]
}

/**
 * One bubble: yours on the right (with the receipt you attached, if any), the assistant's on the left. The
 * assistant's tool chips come first, then its cards or forms (they arrive with a tool's result), then its text,
 * because the tools run before it answers. A message with no text (a receipt sent alone) shows no text box.
 *
 * Memoised: while a reply streams, only its own bubble draws again, not every earlier bubble and card (charts
 * included). That needs stable `onFormChange` and `onFormSubmit` functions, which useChat provides.
 */
export const ChatMessageBubble = memo(function ChatMessageBubble({
  message,
  formsLocked,
  onFormChange,
  onFormSubmit,
}: ChatMessageBubbleProps) {
  const isUser = message.role === MESSAGE_ROLES.user

  // The chips' row is a polite live region, so screen readers announce them as they change ("Expense saved").
  // An assistant reply can be chips only for a moment, before its text arrives, so the text box waits for text.
  // whitespace-pre-wrap keeps the line breaks in the assistant's text.
  return (
    <div className={cn("flex flex-col gap-1.5", isUser ? "items-end" : "items-start")}>
      {message.tools && message.tools.length > 0 && (
        <div className="flex max-w-[85%] flex-wrap gap-1" aria-live="polite">
          {message.tools.map((tool) => (
            <ToolChip key={tool.id} tool={tool} />
          ))}
        </div>
      )}

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

      {message.attachment && <AttachedFile name={message.attachment} />}

      {message.text && (
        <div
          className={cn(
            "max-w-[85%] rounded-lg px-3 py-2 text-sm wrap-break-word whitespace-pre-wrap",
            bubbleStyle(message),
          )}
        >
          {message.text}
        </div>
      )}
    </div>
  )
})
