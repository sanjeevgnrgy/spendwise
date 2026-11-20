// What a click on an A2UI Button does: send its event to the agent, or run one of the allow-listed client functions
// (a report download, D209). Part of the assistant feature's A2UI renderer; used by A2uiButton (basic-components.tsx).

import { useState } from "react"
import { toast } from "sonner"

import { isAbort, messageOf, reportUnexpected } from "@/shared/lib/errors"

import { buildAction, readAction } from "./actions"
import { readFunctionCall } from "./functions/client-functions"
import type { A2uiComponent, A2uiRenderContext } from "./protocol"

/**
 * The click handler for a Button, or null when it can't be clicked: an event with nobody listening or on a locked
 * surface, a function call that isn't allowed, or a function that's still running. A client function doesn't involve
 * the agent, so it works on a locked surface too (an older card's download); a failure is shown in a toast.
 */
export function useButtonClick(node: A2uiComponent, ctx: A2uiRenderContext): (() => void) | null {
  const [running, setRunning] = useState(false)
  const run = readFunctionCall(node.action)
  if (run) {
    if (running) return null
    return () => {
      setRunning(true)
      run()
        .catch((error: unknown) => {
          if (isAbort(error)) return
          reportUnexpected(error)
          toast.error(messageOf(error))
        })
        .finally(() => setRunning(false))
    }
  }
  const event = readAction(node.action)
  if (event === null || ctx.onAction === undefined || ctx.locked) return null
  // The time is taken at the click; buildAction itself stays pure.
  return () => ctx.onAction?.(buildAction(event, ctx.surface, node.id, new Date()))
}
