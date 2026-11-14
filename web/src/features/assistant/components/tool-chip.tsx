// A component of the assistant feature: one tool call as a small status chip in the assistant's bubble. Used by
// ChatMessageBubble (chat-message.tsx), once per tool the reply used.

import { Check, CircleHelp, Loader2, X } from "lucide-react"

import { Badge } from "@/shared/ui/badge"

import type { ToolActivity } from "../model/chat-types"

const NOT_CONFIRMED = "The connection was lost before the result arrived. The pages have been reloaded."

/**
 * One tool call as a chip: spinning while it runs, then a tick or a cross, or "?" if the connection broke while
 * it ran. What it says comes from the backend (TOOL_CALL_START's labels), so this file knows no tool names.
 */
export function ToolChip({ tool }: { tool: ToolActivity }) {
  const { running, done, failed } = tool.labels

  if (tool.status === "running") {
    return (
      <Badge variant="outline">
        <Loader2 className="animate-spin" /> {running}
      </Badge>
    )
  }
  if (tool.status === "unknown") {
    // The connection broke while it ran: it may or may not have finished. Don't claim either.
    return (
      <Badge variant="outline" title={NOT_CONFIRMED}>
        <CircleHelp /> {done}?<span className="sr-only"> {NOT_CONFIRMED}</span>
      </Badge>
    )
  }
  if (tool.status === "failed") {
    // Hover to see why (e.g. "Unknown category"); the reply usually explains too. The reason is also in a
    // screen-reader-only span, because a title alone isn't read reliably.
    return (
      <Badge variant="destructive" title={tool.result}>
        <X /> {failed}
        {tool.result && <span className="sr-only">: {tool.result}</span>}
      </Badge>
    )
  }
  return (
    <Badge variant="secondary">
      <Check /> {done}
    </Badge>
  )
}
