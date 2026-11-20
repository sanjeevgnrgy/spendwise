// The conversation's message list and every change made to it, as pure functions: each takes the messages and
// returns the next list, never changing the old one (React state). use-chat.ts calls them inside setMessages;
// they hold the rules for where a reply, a chip, a card and an error bubble go, so those rules can be checked
// without React or a network. The few texts they write ("Stopped.", "Sent: …") are read from the assistant's
// texts when the bubble is made, so a bubble stays in the language it was made in.

import { EventType } from "@ag-ui/core"

import { AGUI } from "@/shared/api/contracts.gen"
import { i18n } from "@/shared/i18n"
import { isAbort, messageOf } from "@/shared/lib/errors"

import { applyA2uiMessage, createsSurface, setAt, type A2uiAction, type A2uiSurface } from "../a2ui/protocol"
import { toolDetailOf, toolLabelsOf, toolSucceeded } from "../api/agent-events"
import type { AgentEvent } from "../api/agent-stream"
import { connectionLostMessage } from "../api/sse"
import { assistantTexts } from "../i18n"
import type { ChatMessage, ToolActivity } from "./chat-types"

// How a form's values read in your bubble: "Sent: 250 · Food · Subway · 2026-11-13 · upi" (the text
// "transcript.sent", with the values joined by these).
const SENT_SEPARATOR = " · "
const CHOICES_SEPARATOR = ", "

/** The messages with `message` added at the end. */
export function appendMessage(messages: ChatMessage[], message: ChatMessage): ChatMessage[] {
  return [...messages, message]
}

/** The messages with message `id` replaced by `change(it)`; the others stay the same objects. */
export function updateMessage(
  messages: ChatMessage[],
  id: number,
  change: (message: ChatMessage) => ChatMessage,
): ChatMessage[] {
  return messages.map((message) => (message.id === id ? change(message) : message))
}

/** The messages with one surface (card or form) changed, wherever it is in the conversation. */
export function updateSurface(
  messages: ChatMessage[],
  surfaceId: string,
  change: (surface: A2uiSurface) => A2uiSurface,
): ChatMessage[] {
  return messages.map((message) =>
    message.surfaces?.some((surface) => surface.id === surfaceId)
      ? { ...message, surfaces: message.surfaces.map((s) => (s.id === surfaceId ? change(s) : s)) }
      : message,
  )
}

/** The messages with `value` written at `path` in one form's data model. */
export function setFormValue(messages: ChatMessage[], surfaceId: string, path: string, value: unknown): ChatMessage[] {
  return updateSurface(messages, surfaceId, (surface) => ({ ...surface, data: setAt(surface.data, path, value) }))
}

/** The messages with one card or form locked (sent: its inputs and buttons are disabled) or unlocked. */
export function setSubmitted(messages: ChatMessage[], surfaceId: string, submitted: boolean): ChatMessage[] {
  return updateSurface(messages, surfaceId, (surface) => ({ ...surface, submitted }))
}

// The reply's bubble, added at the end the first time something arrives for it (text, a chip or a new card).
function withReply(messages: ChatMessage[], replyId: number): ChatMessage[] {
  if (messages.some((message) => message.id === replyId)) return messages
  return appendMessage(messages, { id: replyId, role: "assistant", text: "", tools: [] })
}

function updateTool(
  messages: ChatMessage[],
  replyId: number,
  toolId: string,
  change: (tool: ToolActivity) => ToolActivity,
): ChatMessage[] {
  return updateMessage(messages, replyId, (message) => ({
    ...message,
    tools: message.tools?.map((tool) => (tool.id === toolId ? change(tool) : tool)),
  }))
}

// A2UI rides in AG-UI's CUSTOM event. A new card or form belongs to this reply; an update or delete may be for
// a card from an earlier reply, so it's offered to every message that has cards.
function applyA2ui(messages: ChatMessage[], replyId: number, value: unknown): ChatMessage[] {
  if (createsSurface(value)) {
    return updateMessage(withReply(messages, replyId), replyId, (message) => ({
      ...message,
      surfaces: applyA2uiMessage(message.surfaces ?? [], value),
    }))
  }
  return messages.map((m) => (m.surfaces ? { ...m, surfaces: applyA2uiMessage(m.surfaces, value) } : m))
}

/**
 * The messages after one event of the run whose reply is `replyId`. The reply's bubble is created by the first
 * text, tool call or new card. Events that change nothing on screen (RUN_STARTED, TOOL_CALL_END,
 * STATE_SNAPSHOT, other custom events...) return the same array, so React skips the update.
 */
export function applyAgentEvent(messages: ChatMessage[], replyId: number, event: AgentEvent): ChatMessage[] {
  switch (event.type) {
    case EventType.TEXT_MESSAGE_START:
      return withReply(messages, replyId)
    case EventType.TEXT_MESSAGE_CONTENT:
      // Each piece is added the moment it arrives: the reply "types itself".
      return updateMessage(withReply(messages, replyId), replyId, (message) => ({
        ...message,
        text: message.text + event.delta,
      }))
    case EventType.TOOL_CALL_START: {
      const tool: ToolActivity = {
        id: event.toolCallId,
        name: event.toolCallName,
        args: "",
        labels: toolLabelsOf(event.metadata, event.toolCallName),
        status: "running",
      }
      return updateMessage(withReply(messages, replyId), replyId, (message) => ({
        ...message,
        tools: [...(message.tools ?? []), tool],
      }))
    }
    case EventType.TOOL_CALL_ARGS:
      return updateTool(messages, replyId, event.toolCallId, (tool) => ({ ...tool, args: tool.args + event.delta }))
    // TOOL_CALL_END only says the arguments are complete; the chip keeps spinning while the tool runs.
    case EventType.TOOL_CALL_RESULT: {
      const status = toolSucceeded(event.metadata) ? "done" : "failed"
      const detail = toolDetailOf(event.metadata)
      return updateTool(messages, replyId, event.toolCallId, (tool) => ({ ...tool, status, detail }))
    }
    case EventType.CUSTOM:
      return event.name === AGUI.customEvents.a2ui ? applyA2ui(messages, replyId, event.value) : messages
    default:
      return messages
  }
}

/**
 * The messages with the reply's chips in `ids` marked "unknown". For tool calls that were running when the run
 * broke off: each may have finished on the server or not, so the chip says exactly that, never "failed".
 */
export function markToolsUnknown(messages: ChatMessage[], replyId: number, ids: ReadonlySet<string>): ChatMessage[] {
  return updateMessage(messages, replyId, (message) => ({
    ...message,
    tools: message.tools?.map((tool) => (ids.has(tool.id) ? { ...tool, status: "unknown" } : tool)),
  }))
}

/**
 * What your side of the chat shows for a button's click: the button's own message ("Approve deleting #14", from
 * the server), or else the form's non-empty values, e.g. "Sent: 250 · Food · Subway · 2026-11-13 · upi" (in the
 * language on now). Only shown: the agent is sent the action itself, never this text.
 */
export function sentText(action: A2uiAction): string {
  const values = Object.values(action.context)
    .map((value) => (Array.isArray(value) ? value.join(CHOICES_SEPARATOR) : value))
    .filter((value) => value !== "" && value !== null && value !== undefined)
    .join(SENT_SEPARATOR)
  return action.userMessage ?? i18n.t("transcript.sent", { ns: assistantTexts.name, values })
}

/**
 * The bubble a run that ended early adds below whatever already arrived: "Stopped." if it was stopped, else
 * what went wrong. An error written for people (a RUN_ERROR, an API problem, our own) shows its message; any other
 * Error (a bug) only a generic text (messageOf); anything thrown that isn't even an Error, the connection-lost
 * text. Our own texts are in the language on now.
 */
export function endedEarlyMessage(id: number, error: unknown): ChatMessage {
  if (isAbort(error)) {
    const stopped = i18n.t("transcript.stopped", { ns: assistantTexts.name })
    return { id, role: "assistant", text: stopped, status: "stopped" }
  }
  const text = error instanceof Error ? messageOf(error) : connectionLostMessage()
  return { id, role: "assistant", text, status: "failed" }
}
