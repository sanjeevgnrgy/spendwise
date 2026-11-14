// The assistant conversation's view model: what one message, one tool chip and the whole chat look like to the
// panel. Plain types with no logic, so components, the pure transcript functions (transcript.ts), the payload
// decoders (api/agent-events.ts) and the hooks (use-chat.ts, assistant-context.ts) all share one definition.

import type { A2uiAction, A2uiSurface } from "../a2ui/protocol"
import type { ToolLabels } from "../api/agent-events"

/**
 * Where a tool call stands. "unknown": the connection broke (or Stop was pressed) while it ran, so it may have
 * finished on the server, or not.
 */
export type ToolStatus = "running" | "done" | "failed" | "unknown"

/** One tool call the assistant made, as the panel shows it: a chip that changes as events arrive. */
export interface ToolActivity {
  id: string
  name: string
  /** The arguments' JSON, built up from TOOL_CALL_ARGS pieces. */
  args: string
  labels: ToolLabels
  status: ToolStatus
}

/** One bubble in the conversation: yours, or the assistant's. */
export interface ChatMessage {
  id: number
  role: "user" | "assistant"
  text: string
  /** User only: the name of the receipt file sent with the message (the user's own data, shown as it is). */
  attachment?: string
  /** Assistant only: the tools used for this reply, in order. */
  tools?: ToolActivity[]
  /** Assistant only: A2UI cards and forms sent with this reply. */
  surfaces?: A2uiSurface[]
  /** The run failed (the text is the error), or was stopped. */
  status?: "failed" | "stopped"
}

/** The conversation as the panel uses it (from `useAssistant()`): what to show, and what the user can do. */
export interface ChatState {
  messages: ChatMessage[]
  /** A run is in progress: forms are locked, and Send becomes Stop. */
  sending: boolean
  /**
   * Sends a typed message as the next run, with a receipt file if one is attached (then the text may be empty: the
   * file is uploaded, read, and offered as the expense form). Resolves when the run has ended, however it ended.
   */
  send: (text: string, file?: File) => Promise<void>
  /** Stops the run in progress; what already arrived stays. */
  stop: () => void
  /** Typing in a form: the value lands in that form's data model, in the browser only. */
  setFormValue: (surfaceId: string, path: string, value: unknown) => void
  /** A button on a card or form (Save, Approve, Cancel): locks that card and sends its action as the next run. */
  submitForm: (action: A2uiAction) => Promise<void>
  /** Forgets the conversation; the next message starts a new thread on the server. */
  reset: () => void
}
