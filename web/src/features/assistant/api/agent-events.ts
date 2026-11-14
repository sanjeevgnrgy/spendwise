// Reads the parts of AG-UI events that @ag-ui/core leaves open (`metadata`, `content`, `snapshot`): the chip
// labels, whether a tool worked, a tool's result text, and the shared data version. Pure functions over network
// data, which is checked rather than trusted. Used by the transcript (model/transcript.ts) and the run hook
// (model/use-agent-run.ts).

import { AGUI } from "@/shared/api/contracts.gen"
import { isObject } from "@/shared/lib/guards"


/** What a tool's chip says while it runs, and after it worked or failed. The backend sends them. */
export interface ToolLabels {
  running: string
  done: string
  failed: string
}

// The type of a content part that carries text (AG-UI 1.0 tool results can be a list of parts).
const TEXT_PART = "text"

/**
 * The chip labels the backend sends in TOOL_CALL_START's metadata. It always sends them; the tool's own name
 * is only a last resort, so a chip is never empty.
 */
export function toolLabelsOf(metadata: unknown, name: string): ToolLabels {
  const labels = isObject(metadata) ? metadata[AGUI.metadata.labels] : undefined
  if (
    isObject(labels) &&
    typeof labels.running === "string" &&
    typeof labels.done === "string" &&
    typeof labels.failed === "string"
  ) {
    return { running: labels.running, done: labels.done, failed: labels.failed }
  }
  return { running: name, done: name, failed: name }
}

/** Whether a tool call worked, from TOOL_CALL_RESULT's metadata. Only an explicit `ok: false` means it failed. */
export function toolSucceeded(metadata: unknown): boolean {
  return !(isObject(metadata) && metadata[AGUI.metadata.ok] === false)
}

/** A tool result's content as text: plain text, or (in AG-UI 1.0) a list of parts, of which the text is kept. */
export function toolResultText(content: unknown): string {
  if (typeof content === "string") return content
  if (!Array.isArray(content)) return ""
  return content
    .map((part) => (isObject(part) && part.type === TEXT_PART && typeof part.text === "string" ? part.text : ""))
    .join("")
}

/** The data version in a STATE_SNAPSHOT, or undefined if it doesn't carry a number. */
export function dataVersionOf(snapshot: unknown): number | undefined {
  const version = isObject(snapshot) ? snapshot[AGUI.stateDataVersion] : undefined
  return typeof version === "number" ? version : undefined
}
