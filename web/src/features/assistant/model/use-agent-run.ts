// The run lifecycle: one agent run at a time on this conversation's thread, with the shared data version, Stop,
// and the "sending" flag. Knows nothing about messages: use-chat.ts passes handlers that turn a run's events
// into the conversation. The transport (`runAgent`) is passed in, so the hook can be driven without a network.

import { EventType } from "@ag-ui/core"
import { useCallback, useRef, useState } from "react"

import { newId } from "@/shared/lib/ids"

import { dataVersionOf } from "../api/agent-events"
import type { AgentEvent, AgentPrompt, RunAgent } from "../api/agent-stream"

/** What a run reports to its caller as it goes. */
export interface RunHandlers {
  /** Each event, as soon as it arrives. */
  onEvent: (event: AgentEvent) => void
  /** The run ended without finishing: stopped (an AbortError), a server error, or a broken connection. */
  onFailed: (error: unknown) => void
}

/**
 * Runs the agent. `run(prompt, handlers)` resolves to true if the run finished, false if it failed (after
 * `handlers.onFailed`, and once `sending` has been set back to false). `stop()` ends the run in progress;
 * `forgetThread()` makes the next run start a new thread. The functions keep their identity across renders.
 */
export function useAgentRun(runAgentFn: RunAgent) {
  const [sending, setSending] = useState(false)
  // Refs, not state: changing them shouldn't re-render anything.
  const threadId = useRef<string | null>(null)
  const dataVersion = useRef(0) // the AG-UI shared state, sent with every run
  const controller = useRef<AbortController | null>(null) // the run in progress, so Stop can end it

  const run = useCallback(
    async (prompt: AgentPrompt, handlers: RunHandlers): Promise<boolean> => {
      setSending(true)
      // With AG-UI the client names the thread; the server starts it when the first message arrives.
      threadId.current ??= newId()
      const abort = new AbortController()
      controller.current = abort
      const onEvent = (event: AgentEvent) => {
        // A tool changed expenses: remember the new version, so the next run sends it.
        if (event.type === EventType.STATE_SNAPSHOT) {
          dataVersion.current = dataVersionOf(event.snapshot) ?? dataVersion.current
        }
        handlers.onEvent(event)
      }
      try {
        await runAgentFn(threadId.current, prompt, dataVersion.current, onEvent, abort.signal)
        return true
      } catch (error) {
        handlers.onFailed(error)
        return false
      } finally {
        controller.current = null
        setSending(false)
      }
    },
    [runAgentFn],
  )

  // Stop the run in progress: the connection closes, and what already arrived stays.
  const stop = useCallback(() => {
    controller.current?.abort()
  }, [])

  const forgetThread = useCallback(() => {
    threadId.current = null
  }, [])

  return { sending, run, stop, forgetThread }
}
