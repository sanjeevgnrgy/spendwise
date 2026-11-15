// The assistant's run, streamed: POST /api/v1/agent, then read the answer as AG-UI events over Server-Sent
// Events (framing in sse.ts), each validated with @ag-ui/core's own schemas. The only file that talks to the
// agent endpoint. model/use-agent-run.ts calls `runAgent` (injectable, see RunAgent); the model files use its
// types.

import { EventType, type Event as AgentEvent, type RunAgentInput, type UserMessage } from "@ag-ui/core"
import { EventSchemas } from "@ag-ui/core/schemas"

import { A2UI, AGUI } from "@/shared/api/contracts.gen"
import { ApiError, apiHeaders, unreachableError } from "@/shared/api/http"
import type { paths } from "@/shared/api/schema.gen"
import { i18n } from "@/shared/i18n"
import { isAbort, UserFacingError } from "@/shared/lib/errors"
import { newId } from "@/shared/lib/ids"

import type { A2uiAction } from "../a2ui/protocol"
import { assistantTexts } from "../i18n"
import { receiptPart, uploadReceipt, type Receipt } from "./receipts"
import { connectionLostMessage, sseData } from "./sse"

/** One AG-UI event, as validated by @ag-ui/core. */
export type { AgentEvent }

/**
 * What starts a run: something typed (possibly empty, with a receipt `file` attached), or a button's click (an A2UI
 * `action`).
 */
export type AgentPrompt = { text: string; file?: File } | { action: A2uiAction }

// Checked against the API's paths, like every other call (a typo is a compile error). Relative, like the API
// client's: the API is on the page's own origin (D184).
const AGENT_PATH = "/api/v1/agent" satisfies keyof paths
const USER_ROLE = "user"
// AG-UI's text content part (a receipt travels as a media part: receipts.ts).
const TEXT_PART = "text"

// The message when an event can't be read. A function, so it's written in the language on when that happens.
function notUnderstoodMessage(): string {
  return i18n.t("stream.notUnderstood", { ns: assistantTexts.name })
}

/** The run itself failed on the server (RUN_ERROR): its message is written for people; its code is the kind. */
export class AgentRunError extends UserFacingError {
  readonly code?: string

  constructor(message: string, code?: string) {
    super(message)
    this.code = code
  }
}

/**
 * A user message's content: the text alone, or (with a receipt) the text, if any, then the receipt as an image or
 * document part pointing at the uploaded file. The server reads the file it holds; no bytes travel here.
 */
export function messageContent(text: string, receipt?: Receipt): UserMessage["content"] {
  if (!receipt) return text
  return text ? [{ type: TEXT_PART, text }, receiptPart(receipt)] : [receiptPart(receipt)]
}

/**
 * AG-UI's run input. The browser names the thread; the server only needs the newest message, because it keeps
 * the conversation's history itself. `dataVersion` is the shared state as this browser knows it: the server
 * sends it back, raised, when data changed. `receipt` is the prompt's file, already uploaded.
 */
export function runInput(
  threadId: string,
  prompt: AgentPrompt,
  dataVersion: number,
  receipt?: Receipt,
): RunAgentInput {
  return {
    threadId,
    runId: newId(),
    state: { [AGUI.stateDataVersion]: dataVersion },
    messages: "text" in prompt ? [{ id: newId(), role: USER_ROLE, content: messageContent(prompt.text, receipt) }] : [],
    tools: [],
    context: [],
    // A click is an A2UI action message. AG-UI has no official place for one, so it goes in
    // forwardedProps, AG-UI's field for extra data from the client (decisions D124).
    forwardedProps:
      "action" in prompt ? { [AGUI.forwardedA2uiAction]: { version: A2UI.version, action: prompt.action } } : {},
  }
}

/** One event's data, as a valid AG-UI event. Throws a UserFacingError if it isn't JSON or isn't a valid event. */
export function parseEvent(data: string): AgentEvent {
  let json: unknown
  try {
    json = JSON.parse(data)
  } catch {
    throw new UserFacingError(notUnderstoodMessage())
  }
  // Network data is checked, not trusted: AG-UI's own schemas say what a valid event looks like.
  const parsed = EventSchemas.safeParse(json)
  if (!parsed.success) throw new UserFacingError(notUnderstoodMessage())
  return parsed.data
}

// Sends the run and returns the answer's body, decoded to text. An attached file is uploaded first (so Stop stops
// that too). Anything that fails while sending is an ApiError (unreachableError()), unless it was stopped. Problems
// found before the stream starts (a refused file, a malformed body) are ordinary HTTP problems: an ApiError with the
// problem's message.
async function startRun(
  threadId: string,
  prompt: AgentPrompt,
  dataVersion: number,
  signal?: AbortSignal,
): Promise<ReadableStream<string>> {
  const receipt = "file" in prompt && prompt.file ? await uploadReceipt(prompt.file, signal) : undefined
  let response: Response
  try {
    // fetch, not EventSource: EventSource can only send GET requests, and a run needs a POST body.
    response = await fetch(AGENT_PATH, {
      method: "POST",
      // The headers every API call carries: the run's language (the server writes its cards, progress labels and
      // errors in it, and the model replies in it) and X-CSRF.
      headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...apiHeaders() },
      body: JSON.stringify(runInput(threadId, prompt, dataVersion, receipt)),
      signal,
    })
  } catch (error) {
    if (isAbort(error)) throw error
    throw unreachableError()
  }
  if (!response.ok || !response.body) {
    throw ApiError.fromProblem(await response.json().catch(() => null), response.status)
  }
  return response.body.pipeThrough(new TextDecoderStream())
}

/**
 * Runs the assistant once, calling `onEvent` for each event as soon as it arrives. Resolves on RUN_FINISHED.
 * Throws AgentRunError on RUN_ERROR, ApiError if the request itself fails, an AbortError if `signal` stops it,
 * or a UserFacingError if an event can't be read or the connection ends before the run does.
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
  throw new UserFacingError(connectionLostMessage())
}

/** The shape of `runAgent`, so a test (or another transport) can be passed to useChat in its place. */
export type RunAgent = typeof runAgent
