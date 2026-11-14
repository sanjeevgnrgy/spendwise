// What one run has done so far that matters if it breaks off: which tool calls are still running, and whether
// data changed. Pure and immutable: `trackEvent` returns the next value. use-chat.ts folds every event of a run
// into it, then uses it to mark unfinished chips "?" and to decide whether a form may be sent again.

import { EventType } from "@ag-ui/core"

import type { AgentEvent } from "../api/agent-stream"

/** One run's progress: the tool calls started but not yet answered, and whether a tool changed data. */
export interface RunProgress {
  readonly running: ReadonlySet<string>
  readonly changedData: boolean
}

/** The progress of a run that has just started. Never changed: `trackEvent` always copies. */
export const NEW_RUN: RunProgress = { running: new Set(), changedData: false }

/** The progress after `event`. Events that don't affect it return the same object. */
export function trackEvent(progress: RunProgress, event: AgentEvent): RunProgress {
  switch (event.type) {
    case EventType.TOOL_CALL_START:
      return { ...progress, running: new Set(progress.running).add(event.toolCallId) }
    case EventType.TOOL_CALL_RESULT: {
      if (!progress.running.has(event.toolCallId)) return progress
      const running = new Set(progress.running)
      running.delete(event.toolCallId)
      return { ...progress, running }
    }
    // The server raises the data version only when a tool changed expenses.
    case EventType.STATE_SNAPSHOT:
      return progress.changedData ? progress : { ...progress, changedData: true }
    default:
      return progress
  }
}

/**
 * True if the server changed data during the run, or might have: a tool finished with a change, or was still
 * running when the run broke off (it may have finished on the server).
 */
export function mayHaveChanged(progress: RunProgress): boolean {
  return progress.changedData || progress.running.size > 0
}
