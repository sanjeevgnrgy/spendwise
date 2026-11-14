// A component of the assistant feature: one tool call as a small status chip in the assistant's bubble. Used by
// ChatMessageBubble (chat-message.tsx), once per tool the reply used.

import { Check, CircleHelp, Loader2, X } from "lucide-react"

import { Badge } from "@/shared/ui/badge"

import { useTexts } from "../i18n"
import type { ToolActivity } from "../model/chat-types"

/**
 * One tool call as a chip: spinning while it runs, then a tick or a cross, or "?" if the connection broke while
 * it ran. What it says comes from the backend (TOOL_CALL_START's labels, shown as sent), so this file knows no
 * tool names; only the "?" chip's explanation is the browser's own text, in the language on now.
 */
export function ToolChip({ tool }: { tool: ToolActivity }) {
  const { t } = useTexts()
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
    const notConfirmed = t("chips.notConfirmed")
    return (
      <Badge variant="outline" title={notConfirmed}>
        <CircleHelp /> {done}?<span className="sr-only"> {notConfirmed}</span>
      </Badge>
    )
  }
  if (tool.status === "failed") {
    // Only that it failed: the tool's own reason is written for the model and stays on the server (D180). The
    // reply explains what went wrong, in the user's language.
    return (
      <Badge variant="destructive">
        <X /> {failed}
      </Badge>
    )
  }
  return (
    <Badge variant="secondary">
      <Check /> {done}
    </Badge>
  )
}
