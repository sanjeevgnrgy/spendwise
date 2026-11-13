import { Check, CircleHelp, Loader2, X } from "lucide-react"

import { Badge } from "@/shared/ui/badge"

import type { ToolActivity } from "../model/use-chat"

const NOT_CONFIRMED = "The connection was lost before the result arrived. The pages have been reloaded."

// One tool call as a small status chip: spinning while it runs, then a tick or a cross. What it says
// comes from the backend (TOOL_CALL_START's labels), so this file knows no tool names.
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
    // Hover to see why (e.g. "Unknown category"); the reply usually explains too.
    return (
      <Badge variant="destructive" title={tool.result}>
        <X /> {failed}
        {/* The reason, for screen readers too (a title alone isn't read reliably). */}
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
