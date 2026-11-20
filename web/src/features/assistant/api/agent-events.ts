// Reads the parts of AG-UI events that @ag-ui/core leaves open (`metadata`, `snapshot`): the chip labels, whether
// a tool worked and the remote agent's task, and the shared data version. (A tool's result text stays on the server,
// D180.) Pure functions over network data, which is checked rather than trusted. Used by the transcript
// (model/transcript.ts) and the run hook (model/use-agent-run.ts).

import { AGUI } from "@/shared/api/contracts.gen"
import { isObject } from "@/shared/lib/guards"


/** What a tool's chip says while it runs, and after it worked or failed. The backend sends them. */
export interface ToolLabels {
  running: string
  done: string
  failed: string
}

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

/**
 * What the chip adds after its text, from TOOL_CALL_RESULT's metadata: the remote agent's task when one did the work
 * ("A2A task 3f2a9c1e", written by the server in the run's language), or undefined.
 */
export function toolDetailOf(metadata: unknown): string | undefined {
  const detail = isObject(metadata) ? metadata[AGUI.metadata.detail] : undefined
  return typeof detail === "string" && detail !== "" ? detail : undefined
}

/** The data version in a STATE_SNAPSHOT, or undefined if it doesn't carry a number. */
export function dataVersionOf(snapshot: unknown): number | undefined {
  const version = isObject(snapshot) ? snapshot[AGUI.stateDataVersion] : undefined
  return typeof version === "number" ? version : undefined
}
