// The assistant conversation's view model: what one message, one tool chip and the whole chat look like to the
// panel, and the names of their roles and statuses. Types and constants with no logic, so components, the pure
// transcript functions (transcript.ts), the payload decoders (api/agent-events.ts) and the hooks (use-chat.ts,
// assistant-context.ts) all share one definition.

import type { A2uiAction, A2uiSurface } from "../a2ui/protocol"
import type { ToolLabels } from "../api/agent-events"

/**
 * Where a tool call stands. `unknown`: the connection broke (or Stop was pressed) while it ran, so it may have
 * finished on the server, or not.
 */
export const TOOL_STATUSES = { running: "running", done: "done", failed: "failed", unknown: "unknown" } as const
/** One of TOOL_STATUSES' values. */
export type ToolStatus = (typeof TOOL_STATUSES)[keyof typeof TOOL_STATUSES]

/** Who wrote a message: the person, or the assistant. */
export const MESSAGE_ROLES = { user: "user", assistant: "assistant" } as const
/** One of MESSAGE_ROLES' values. */
export type MessageRole = (typeof MESSAGE_ROLES)[keyof typeof MESSAGE_ROLES]

/** How an assistant reply ended, when it didn't end normally: the run failed, or was stopped. */
export const MESSAGE_STATUSES = { failed: "failed", stopped: "stopped" } as const
/** One of MESSAGE_STATUSES' values. */
export type MessageStatus = (typeof MESSAGE_STATUSES)[keyof typeof MESSAGE_STATUSES]

/** One tool call the assistant made, as the panel shows it: a chip that changes as events arrive. */
export interface ToolActivity {
  id: string
  name: string
  /** The arguments' JSON, built up from TOOL_CALL_ARGS pieces. */
  args: string
  labels: ToolLabels
  status: ToolStatus
  /** Shown after the chip's text once it has run: the remote agent's task, when one did the work (from the server). */
  detail?: string
}

/** One bubble in the conversation: yours, or the assistant's. */
export interface ChatMessage {
  id: number
  role: MessageRole
  text: string
  /** User only: the name of the receipt file sent with the message (the user's own data, shown as it is). */
  attachment?: string
  /** Assistant only: the tools used for this reply, in order. */
  tools?: ToolActivity[]
  /** Assistant only: A2UI cards and forms sent with this reply. */
  surfaces?: A2uiSurface[]
  /** The run failed (the text is the error), or was stopped. */
  status?: MessageStatus
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
