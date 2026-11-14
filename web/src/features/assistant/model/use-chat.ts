// The conversation, as a custom hook: it holds the messages and wires the run (use-agent-run.ts) to the pure
// transcript changes (transcript.ts) and the run's progress (run-progress.ts). Orchestration only: the rules
// live in those files. AssistantProvider calls it once and shares the result through AssistantContext.

import { EventType } from "@ag-ui/core"
import { useCallback, useMemo, useRef, useState } from "react"

import { reportUnexpected } from "@/shared/lib/errors"

import type { A2uiAction } from "../a2ui/protocol"
import { runAgent, type AgentPrompt, type RunAgent } from "../api/agent-stream"
import type { ChatMessage, ChatState } from "./chat-types"
import { mayHaveChanged, NEW_RUN, trackEvent } from "./run-progress"
import * as transcript from "./transcript"
import { useAgentRun } from "./use-agent-run"

/**
 * Everything about the conversation. `onDataChanged` is called whenever the assistant may have changed
 * expenses; this feature doesn't know (or care) which pages show them. `runAgentFn` is the transport, `runAgent`
 * unless a test passes its own. The functions returned keep their identity across renders (for memoised
 * bubbles), as long as `onDataChanged` and `runAgentFn` do.
 */
export function useChat(onDataChanged: () => void, runAgentFn: RunAgent = runAgent): ChatState {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const nextId = useRef(0) // a counter for message ids (a ref: changing it shouldn't re-render anything)
  const { sending, run: runAgentOnce, stop, forgetThread } = useAgentRun(runAgentFn)

  // One run of the agent. `shown` is what appears in your bubble. Resolves to whether the run finished, and
  // whether the server changed data during it, or might have.
  const run = useCallback(
    async (shown: string, prompt: AgentPrompt) => {
      const userId = nextId.current++
      const replyId = nextId.current++ // reserved now; the bubble appears when the first text, chip or card does
      setMessages((current) => transcript.appendMessage(current, { id: userId, role: "user", text: shown }))
      let progress = NEW_RUN
      const ok = await runAgentOnce(prompt, {
        onEvent: (event) => {
          progress = trackEvent(progress, event)
          // A tool changed expenses: let the pages know.
          if (event.type === EventType.STATE_SNAPSHOT) onDataChanged()
          setMessages((current) => transcript.applyAgentEvent(current, replyId, event))
        },
        onFailed: (error) => {
          // The bubble shows only a generic text for a bug, so its details go to the console.
          reportUnexpected(error)
          // A tool was running when the run broke off (or Stop was pressed): its chip says "?", and the pages
          // reload to show what happened.
          const unfinished = progress.running
          if (unfinished.size > 0) {
            setMessages((current) => transcript.markToolsUnknown(current, replyId, unfinished))
            onDataChanged()
          }
          // Any text that already arrived stays; the error (or "Stopped.") appears as its own bubble below it.
          const endId = nextId.current++
          setMessages((current) => transcript.appendMessage(current, transcript.endedEarlyMessage(endId, error)))
        },
      })
      return { ok, mayHaveChanged: mayHaveChanged(progress) }
    },
    [onDataChanged, runAgentOnce],
  )

  const send = useCallback(
    async (text: string) => {
      await run(text, { text })
    },
    [run],
  )

  const setFormValue = useCallback((surfaceId: string, path: string, value: unknown) => {
    setMessages((current) => transcript.setFormValue(current, surfaceId, path, value))
  }, [])

  // Lock the card first (it decides once), then send its action as the next run.
  const submitForm = useCallback(
    async (action: A2uiAction) => {
      setMessages((current) => transcript.setSubmitted(current, action.surfaceId, true))
      const outcome = await run(transcript.sentText(action), { action })
      // Unlock only if the run failed before anything could have changed. If the expense may already be saved
      // (a tool finished, or was still running when the run broke off), sending the form again could save it twice.
      if (!outcome.ok && !outcome.mayHaveChanged) {
        setMessages((current) => transcript.setSubmitted(current, action.surfaceId, false))
      }
    },
    [run],
  )

  const reset = useCallback(() => {
    setMessages([])
    forgetThread()
  }, [forgetThread])

  return useMemo(
    () => ({ messages, sending, send, stop, setFormValue, submitForm, reset }),
    [messages, sending, send, stop, setFormValue, submitForm, reset],
  )
}
