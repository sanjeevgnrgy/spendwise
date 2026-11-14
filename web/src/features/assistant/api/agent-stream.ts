// The assistant's run, streamed: POST /api/v1/agent, then read the answer as AG-UI events over Server-Sent
// Events (framing in sse.ts), each validated with @ag-ui/core's own schemas. The only file that talks to the
// agent endpoint. model/use-agent-run.ts calls `runAgent` (injectable, see RunAgent); the model files use its
// types.

import { EventType, type Event as AgentEvent, type RunAgentInput } from "@ag-ui/core"
import { EventSchemas } from "@ag-ui/core/schemas"

import { A2UI, AGUI } from "@/shared/api/contracts.gen"
import { ApiError, UNREACHABLE } from "@/shared/api/http"
import type { paths } from "@/shared/api/schema.gen"
import { API_ORIGIN } from "@/shared/config/env"
import { isAbort } from "@/shared/lib/errors"
import { newId } from "@/shared/lib/ids"

import type { A2uiAction } from "../a2ui/protocol"
import { CONNECTION_LOST, sseData } from "./sse"

/** One AG-UI event, as validated by @ag-ui/core. */
export type { AgentEvent }

/** What starts a run: something typed, or a button's click (an A2UI `action`). */
export type AgentPrompt = { text: string } | { action: A2uiAction }

// Checked against the API's paths, like every other call (a typo is a compile error).
const AGENT_PATH = "/api/v1/agent" satisfies keyof paths
const USER_ROLE = "user"
const NOT_UNDERSTOOD = "The assistant sent something this app doesn't understand."

/** The run itself failed on the server (RUN_ERROR): its message is meant for the user. */
export class AgentRunError extends Error {
  readonly code?: string

  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

/**
 * AG-UI's run input. The browser names the thread; the server only needs the newest message, because it keeps
 * the conversation's history itself. `dataVersion` is the shared state as this browser knows it: the server
 * sends it back, raised, when data changed.
 */
export function runInput(threadId: string, prompt: AgentPrompt, dataVersion: number): RunAgentInput {
  return {
    threadId,
    runId: newId(),
    state: { [AGUI.stateDataVersion]: dataVersion },
    messages: "text" in prompt ? [{ id: newId(), role: USER_ROLE, content: prompt.text }] : [],
    tools: [],
    context: [],
    // A click is an A2UI action message. AG-UI has no official place for one, so it goes in
    // forwardedProps, AG-UI's field for extra data from the client (decisions D124).
    forwardedProps:
      "action" in prompt ? { [AGUI.forwardedA2uiAction]: { version: A2UI.version, action: prompt.action } } : {},
  }
}

/** One event's data, as a valid AG-UI event. Throws a plain Error if it isn't JSON or isn't a valid event. */
export function parseEvent(data: string): AgentEvent {
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

// Sends the run and returns the answer's body, decoded to text. Anything that fails while sending is an
// ApiError (UNREACHABLE), unless it was stopped. Problems found before the stream starts (like a malformed body)
// are ordinary HTTP problems: an ApiError with the problem's message.
async function startRun(
  threadId: string,
  prompt: AgentPrompt,
  dataVersion: number,
  signal?: AbortSignal,
): Promise<ReadableStream<string>> {
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
  if (!response.ok || !response.body) {
    throw ApiError.fromProblem(await response.json().catch(() => null), response.status)
  }
  return response.body.pipeThrough(new TextDecoderStream())
}

/**
 * Runs the assistant once, calling `onEvent` for each event as soon as it arrives. Resolves on RUN_FINISHED.
 * Throws AgentRunError on RUN_ERROR, ApiError if the request itself fails, an AbortError if `signal` stops it,
 * or an Error if an event can't be read or the connection ends before the run does.
 */
export async function runAgent(
  threadId: string,
  prompt: AgentPrompt,
  dataVersion: number,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const body = await startRun(threadId, prompt, dataVersion, signal)
  // Leaving this loop early (return or throw) cancels the reader, which closes the connection.
  for await (const data of sseData(body)) {
    const event = parseEvent(data)
    if (event.type === EventType.RUN_ERROR) throw new AgentRunError(event.message, event.code)
    onEvent(event)
    if (event.type === EventType.RUN_FINISHED) return
  }
  throw new Error(CONNECTION_LOST)
}

/** The shape of `runAgent`, so a test (or another transport) can be passed to useChat in its place. */
export type RunAgent = typeof runAgent
