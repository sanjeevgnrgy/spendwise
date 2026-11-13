// The assistant's run, streamed: POST /agent, read as AG-UI events over Server-Sent Events.

import { EventType, type Event as AgentEvent, type RunAgentInput } from "@ag-ui/core"
import { EventSchemas } from "@ag-ui/core/schemas"

import { A2UI, AGUI } from "@/shared/api/contracts.gen"
import { ApiError, UNREACHABLE } from "@/shared/api/http"
import type { paths } from "@/shared/api/schema.gen"
import { API_ORIGIN } from "@/shared/config/env"
import { isAbort } from "@/shared/lib/errors"
import { newId } from "@/shared/lib/ids"

import type { A2uiAction } from "../a2ui/protocol"

export type { AgentEvent }

// What starts a run: something typed, or a button's click (an A2UI `action`).
export type AgentPrompt = { text: string } | { action: A2uiAction }

// Checked against the API's paths, like every other call (a typo is a compile error).
const AGENT_PATH = "/api/v1/agent" satisfies keyof paths
const SSE_EVENT_END = "\n\n"
const SSE_DATA = "data:"
const USER_ROLE = "user"
const NOT_UNDERSTOOD = "The assistant sent something this app doesn't understand."
export const CONNECTION_LOST = "The connection to the assistant was lost before the reply was finished."

// The run itself failed on the server (RUN_ERROR): its message is meant for the user.
export class AgentRunError extends Error {
  readonly code?: string

  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

function runInput(threadId: string, prompt: AgentPrompt, dataVersion: number): RunAgentInput {
  // AG-UI's run input. The browser names the thread; the server only needs the newest message,
  // because it keeps the conversation's history itself.
  return {
    threadId,
    runId: newId(),
    // The shared state, as this browser knows it: the server sends it back, raised, when data changed.
    state: { [AGUI.stateDataVersion]: dataVersion },
    messages: "text" in prompt ? [{ id: newId(), role: USER_ROLE, content: prompt.text }] : [],
    tools: [],
    context: [],
    // A click is an A2UI action message. AG-UI has no official place for one, so it goes in
    // forwardedProps, AG-UI's field for extra data from the client (decisions D124).
    forwardedProps: "action" in prompt ? { [AGUI.forwardedA2uiAction]: { version: A2UI.version, action: prompt.action } } : {},
  }
}

// One SSE event block -> its `data:` lines, joined. FastAPI's ": ping" keep-alive comments have none.
function dataOf(block: string): string {
  return block
    .split("\n")
    .filter((line) => line.startsWith(SSE_DATA))
    .map((line) => line.slice(SSE_DATA.length).trimStart())
    .join("\n")
}

function parseEvent(data: string): AgentEvent {
  let json: unknown
  try {
    json = JSON.parse(data)
  } catch {
    throw new Error(NOT_UNDERSTOOD)
  }
  // Network data is checked, not trusted: AG-UI's own schemas say what a valid event looks like.
  const parsed = EventSchemas.safeParse(json)
  if (!parsed.success) throw new Error(NOT_UNDERSTOOD)
  return parsed.data
}

/**
 * Runs the assistant once, calling `onEvent` for each event as soon as it arrives. Resolves on
 * RUN_FINISHED. Throws AgentRunError on RUN_ERROR, ApiError if the request itself fails, an AbortError
 * if `signal` stops it, or an Error if the connection ends before the run does.
 */
export async function runAgent(
  threadId: string,
  prompt: AgentPrompt,
  dataVersion: number,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    // fetch, not EventSource: EventSource can only send GET requests, and a run needs a POST body.
    response = await fetch(`${API_ORIGIN}${AGENT_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(runInput(threadId, prompt, dataVersion)),
      signal,
    })
  } catch (error) {
    if (isAbort(error)) throw error
    throw new ApiError(UNREACHABLE, 0)
  }
  // Problems found before the stream starts (like a malformed body) are ordinary HTTP problems.
  if (!response.ok || !response.body) {
    throw ApiError.fromProblem(await response.json().catch(() => null), response.status)
  }

  // Read the body piece by piece as it arrives, instead of waiting for all of it like response.json().
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ""
  try {
    for (;;) {
      let piece: ReadableStreamReadResult<string>
      try {
        piece = await reader.read()
      } catch (error) {
        // Stopped on purpose (Stop, or the page closed), or the network dropped mid-reply.
        if (isAbort(error)) throw error
        throw new Error(CONNECTION_LOST)
      }
      const { value, done } = piece
      if (done) break
      buffer += value
      // Each SSE event ends with a blank line. A piece can end mid-event, so keep the unfinished tail.
      const blocks = buffer.split(SSE_EVENT_END)
      buffer = blocks.pop() ?? ""
      for (const block of blocks) {
        const data = dataOf(block)
        if (!data) continue
        const event = parseEvent(data)
        if (event.type === EventType.RUN_ERROR) throw new AgentRunError(event.message, event.code)
        onEvent(event)
        if (event.type === EventType.RUN_FINISHED) return
      }
    }
  } finally {
    // Stop reading and close the connection, however we got here (nothing to do if it already ended).
    reader.cancel().catch(() => {})
  }
  throw new Error(CONNECTION_LOST)
}
