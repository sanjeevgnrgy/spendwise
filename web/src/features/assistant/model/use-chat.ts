import { EventType } from "@ag-ui/core"
import { useRef, useState } from "react"

import { AGUI } from "@/shared/api/contracts.gen"
import { ApiError } from "@/shared/api/http"
import { isAbort, messageOf } from "@/shared/lib/errors"
import { isObject } from "@/shared/lib/guards"
import { newId } from "@/shared/lib/ids"

import { applyA2uiMessage, createsSurface, setAt, type A2uiAction, type A2uiSurface } from "../a2ui/protocol"
import { AgentRunError, CONNECTION_LOST, runAgent, type AgentEvent, type AgentPrompt } from "../api/agent-stream"

// What a tool's chip says while it runs, and after it worked or failed (sent by the backend).
export interface ToolLabels {
  running: string
  done: string
  failed: string
}

// One tool call the assistant made, as the panel shows it: a chip that changes as events arrive.
export interface ToolActivity {
  id: string
  name: string
  args: string // the arguments' JSON, built up from TOOL_CALL_ARGS pieces
  labels: ToolLabels
  // "unknown": the connection broke (or Stop was pressed) while it ran, so it may have finished, or not.
  status: "running" | "done" | "failed" | "unknown"
  result?: string // what the tool returned (for a failed call, why)
}

export interface ChatMessage {
  id: number
  role: "user" | "assistant"
  text: string
  tools?: ToolActivity[] // assistant only: the tools used for this reply, in order
  surfaces?: A2uiSurface[] // assistant only: A2UI cards sent with this reply
  status?: "failed" | "stopped" // the run failed (text is the error), or was stopped
}

interface RunOutcome {
  ok: boolean
  // The server changed expenses on the way, or might have: a tool was still running when the run broke off.
  mayHaveChanged: boolean
}

const STOPPED = "Stopped."
const TEXT_PART = "text"

// A tool result's content: plain text, or (in AG-UI 1.0) a list of parts, of which we show the text.
function plainText(content: unknown): string {
  if (typeof content === "string") return content
  if (!Array.isArray(content)) return ""
  return content.map((part) => (isObject(part) && part.type === TEXT_PART && typeof part.text === "string" ? part.text : "")).join("")
}

// The labels the backend sends with TOOL_CALL_START. (It always sends them; the tool's own name is only
// a last resort, so a chip is never empty.)
function labelsFrom(metadata: unknown, name: string): ToolLabels {
  const labels = isObject(metadata) ? metadata[AGUI.metadata.labels] : undefined
  if (isObject(labels) && typeof labels.running === "string" && typeof labels.done === "string" && typeof labels.failed === "string") {
    return { running: labels.running, done: labels.done, failed: labels.failed }
  }
  return { running: name, done: name, failed: name }
}

// What a failed run says in its red bubble. The server's messages (a RUN_ERROR, an API problem) and our own
// are meant for people; anything else (a value that isn't even an Error) gets a plain explanation.
function failureText(error: unknown): string {
  return error instanceof AgentRunError || error instanceof ApiError || error instanceof Error ? messageOf(error) : CONNECTION_LOST
}

// Everything about the conversation, as a custom hook. `onDataChanged` is called whenever the assistant
// may have changed expenses; this feature doesn't know (or care) which pages show them.
export function useChat(onDataChanged: () => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [threadId, setThreadId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  // Refs, not state: changing them shouldn't re-render anything.
  const nextId = useRef(0) // a counter for message ids
  const dataVersion = useRef(0) // the AG-UI shared state, sent with every run
  const controller = useRef<AbortController | null>(null) // the run in progress, so Stop can end it

  function add(message: Omit<ChatMessage, "id">): number {
    const id = nextId.current++
    setMessages((current) => [...current, { ...message, id }])
    return id
  }

  function update(id: number | null, change: (message: ChatMessage) => ChatMessage) {
    setMessages((current) => current.map((message) => (message.id === id ? change(message) : message)))
  }

  // Change one surface (card or form), wherever it is in the conversation.
  function updateSurface(surfaceId: string, change: (surface: A2uiSurface) => A2uiSurface) {
    setMessages((current) =>
      current.map((message) =>
        message.surfaces?.some((surface) => surface.id === surfaceId)
          ? { ...message, surfaces: message.surfaces.map((s) => (s.id === surfaceId ? change(s) : s)) }
          : message,
      ),
    )
  }

  // Typing in a form: the value lands in that form's data model, in the browser only.
  function setFormValue(surfaceId: string, path: string, value: unknown) {
    updateSurface(surfaceId, (surface) => ({ ...surface, data: setAt(surface.data, path, value) }))
  }

  // A button on a card or form (Save, Approve, Cancel): lock that card (it decides once), then send
  // its action as the next run.
  async function submitForm(action: A2uiAction) {
    updateSurface(action.surfaceId, (surface) => ({ ...surface, submitted: true }))
    // Your side of the chat shows the button's own message ("Approve deleting #14"), or else what a
    // form sent, e.g. "Sent: 250 · Food · Subway · 2026-11-13 · upi".
    const values = Object.values(action.context)
      .map((value) => (Array.isArray(value) ? value.join(", ") : value))
      .filter((value) => value !== "" && value !== null && value !== undefined)
    const { ok, mayHaveChanged } = await run(action.userMessage ?? `Sent: ${values.join(" · ")}`, { action })
    // Unlock only if the run failed before anything could have changed. If the expense may already be saved
    // (a tool finished, or was still running when the run broke off), sending the form again could save it twice.
    if (!ok && !mayHaveChanged) updateSurface(action.surfaceId, (surface) => ({ ...surface, submitted: false }))
  }

  function send(text: string) {
    return run(text, { text })
  }

  // Stop the run in progress: the connection closes, and what already arrived stays.
  function stop() {
    controller.current?.abort()
  }

  // One run of the agent. `shown` is what appears in your bubble.
  async function run(shown: string, prompt: AgentPrompt): Promise<RunOutcome> {
    let changedData = false
    add({ role: "user", text: shown })
    setSending(true)
    // With AG-UI the client names the thread; the server starts it when the first message arrives.
    const thread = threadId ?? newId()
    setThreadId(thread)
    const abort = new AbortController()
    controller.current = abort

    // The reply's bubble, created by whatever arrives first: text, or a tool call.
    let replyId: number | null = null
    const running = new Set<string>() // tool calls started but not yet answered
    const reply = () => (replyId ??= add({ role: "assistant", text: "", tools: [] }))
    const updateTool = (toolId: string, change: (tool: ToolActivity) => ToolActivity) =>
      update(replyId, (message) => ({
        ...message,
        tools: message.tools?.map((tool) => (tool.id === toolId ? change(tool) : tool)),
      }))

    const handle = (event: AgentEvent) => {
      switch (event.type) {
        case EventType.TEXT_MESSAGE_START:
          reply()
          break
        case EventType.TEXT_MESSAGE_CONTENT:
          // Each piece is added the moment it arrives: the reply "types itself".
          update(reply(), (message) => ({ ...message, text: message.text + event.delta }))
          break
        case EventType.TOOL_CALL_START: {
          const tool: ToolActivity = {
            id: event.toolCallId,
            name: event.toolCallName,
            args: "",
            labels: labelsFrom(event.metadata, event.toolCallName),
            status: "running",
          }
          update(reply(), (message) => ({ ...message, tools: [...(message.tools ?? []), tool] }))
          running.add(event.toolCallId)
          break
        }
        case EventType.TOOL_CALL_ARGS:
          updateTool(event.toolCallId, (tool) => ({ ...tool, args: tool.args + event.delta }))
          break
        // TOOL_CALL_END only says the arguments are complete; the chip keeps spinning while the tool runs.
        case EventType.TOOL_CALL_RESULT: {
          const ok = !(isObject(event.metadata) && event.metadata[AGUI.metadata.ok] === false)
          updateTool(event.toolCallId, (tool) => ({ ...tool, status: ok ? "done" : "failed", result: plainText(event.content) }))
          running.delete(event.toolCallId)
          break
        }
        case EventType.STATE_SNAPSHOT: {
          // A tool changed expenses: remember the new version, and let the pages know.
          const version = isObject(event.snapshot) ? event.snapshot[AGUI.stateDataVersion] : undefined
          if (typeof version === "number") dataVersion.current = version
          changedData = true
          onDataChanged()
          break
        }
        case EventType.CUSTOM:
          // A2UI rides in AG-UI's extension event. Custom events with other names are ignored.
          if (event.name !== AGUI.customEvents.a2ui) break
          if (createsSurface(event.value)) {
            // A new card or form belongs to this reply.
            update(reply(), (message) => ({ ...message, surfaces: applyA2uiMessage(message.surfaces ?? [], event.value) }))
          } else {
            // An update or delete may be for a card from an earlier reply: offer it to every one.
            setMessages((current) =>
              current.map((m) => (m.surfaces ? { ...m, surfaces: applyA2uiMessage(m.surfaces, event.value) } : m)),
            )
          }
          break
      }
    }

    try {
      await runAgent(thread, prompt, dataVersion.current, handle, abort.signal)
      return { ok: true, mayHaveChanged: changedData }
    } catch (error) {
      // The connection broke (or Stop was pressed) while a tool ran: it may have finished on the server or
      // not, so say exactly that ("not confirmed", never "failed"), and reload the pages to show what happened.
      if (running.size > 0) {
        update(replyId, (message) => ({
          ...message,
          tools: message.tools?.map((tool) => (running.has(tool.id) ? { ...tool, status: "unknown" } : tool)),
        }))
        onDataChanged()
      }
      // Any text that already arrived stays; the error (or "Stopped.") appears as its own bubble below it.
      if (isAbort(error)) add({ role: "assistant", text: STOPPED, status: "stopped" })
      else add({ role: "assistant", text: failureText(error), status: "failed" })
      return { ok: false, mayHaveChanged: changedData || running.size > 0 }
    } finally {
      controller.current = null
      setSending(false)
    }
  }

  // Forget the conversation; the next message starts a new thread on the server.
  function reset() {
    setMessages([])
    setThreadId(null)
  }

  return { messages, threadId, sending, send, stop, setFormValue, submitForm, reset }
}

export type ChatState = ReturnType<typeof useChat>
