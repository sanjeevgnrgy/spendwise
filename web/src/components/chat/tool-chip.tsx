import { Check, Loader2, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { ToolActivity } from "@/hooks/use-chat"

type Labels = [running: string, done: string, failed: string]

// What a chip says for each tool. Tools not listed here fall back to their own name.
const LABELS: Record<string, Labels> = {
  add_expense: ["Saving expense…", "Expense saved", "Couldn't save expense"],
  update_expense: ["Updating expense…", "Expense updated", "Couldn't update expense"],
  delete_expense: ["Deleting expense…", "Expense deleted", "Couldn't delete expense"],
  list_expenses: ["Looking up expenses…", "Looked up expenses", "Couldn't look up expenses"],
  get_summary: ["Adding up the month…", "Added up the month", "Couldn't add up the month"],
}

// Without confirmed=true, delete_expense only looks the expense up so you can confirm (D53).
// Say exactly that: a chip must never claim something was deleted when it wasn't.
const DELETE_CHECK: Labels = ["Checking the expense…", "Waiting for your OK", "Couldn't find the expense"]

function isConfirmed(args: string): boolean {
  try {
    return JSON.parse(args).confirmed === true
  } catch {
    return false // the arguments haven't fully arrived yet
  }
}

function labelsFor(tool: ToolActivity): Labels {
  if (tool.name === "delete_expense" && !isConfirmed(tool.args)) return DELETE_CHECK
  const name = tool.name.replaceAll("_", " ")
  return LABELS[tool.name] ?? [`Running ${name}…`, `Ran ${name}`, `${name} failed`]
}

// One tool call as a small status chip: spinning while it runs, then a tick or a cross.
export function ToolChip({ tool }: { tool: ToolActivity }) {
  const [running, done, failed] = labelsFor(tool)

  if (tool.status === "running") {
    return (
      <Badge variant="outline">
        <Loader2 className="animate-spin" /> {running}
      </Badge>
    )
  }
  if (tool.status === "failed") {
    // Hover to see why (e.g. "Unknown category"); the reply usually explains too.
    return (
      <Badge variant="destructive" title={tool.result}>
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
