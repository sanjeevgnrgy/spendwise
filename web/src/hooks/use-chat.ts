import { useRef, useState } from "react"

import { newId, runAgent, type AgentPrompt } from "@/api"
import { applyA2uiMessage, setAt, type A2uiAction, type A2uiSurface } from "@/lib/a2ui"
import { useDataSync } from "@/lib/data-sync"

// One tool call the assistant made, as the panel shows it: a chip that changes as events arrive.
export interface ToolActivity {
  id: string
  name: string
  args: string // the arguments' JSON, built up from TOOL_CALL_ARGS pieces
  status: "running" | "done" | "failed"
  result?: string // what the tool returned (for a failed call, why)
}

export interface ChatMessage {
  id: number
  role: "user" | "assistant"
  text: string
  tools?: ToolActivity[] // assistant only: the tools used for this reply, in order
  surfaces?: A2uiSurface[] // assistant only: A2UI cards sent with this reply
  failed?: boolean // the run failed; text is the error
}

// Everything about the conversation, as a custom hook. It's used by the layout (which stays on
// screen across pages), not by the panel, so closing the panel or changing page keeps the chat.
export function useChat() {
  const { dataVersion, setDataVersion } = useDataSync()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [threadId, setThreadId] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  // A counter for message ids. A ref (not state): changing it shouldn't re-render anything.
  const nextId = useRef(0)

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
    const ok = await run(action.userMessage ?? `Sent: ${values.join(" · ")}`, { action })
    // If the run failed, unlock the form so it can be sent again.
    if (!ok) updateSurface(action.surfaceId, (surface) => ({ ...surface, submitted: false }))
  }

  function send(text: string) {
    return run(text, { text })
  }

  // One run of the agent. `shown` is what appears in your bubble. Returns whether the run succeeded.
  async function run(shown: string, prompt: AgentPrompt): Promise<boolean> {
    add({ role: "user", text: shown })
    setSending(true)
    // With AG-UI the client names the thread; the server starts it when the first message arrives.
    const thread = threadId ?? newId()
    setThreadId(thread)

    // The reply's bubble, created by whatever arrives first: text, or a tool call.
    let replyId: number | null = null
    const reply = () => (replyId ??= add({ role: "assistant", text: "", tools: [] }))
    const updateTool = (toolId: string, change: (tool: ToolActivity) => ToolActivity) =>
      update(replyId, (message) => ({
        ...message,
        tools: message.tools?.map((tool) => (tool.id === toolId ? change(tool) : tool)),
      }))

    try {
      await runAgent(thread, prompt, { dataVersion }, (event) => {
        switch (event.type) {
          case "TEXT_MESSAGE_START":
            reply()
            break
          case "TEXT_MESSAGE_CONTENT":
            // Each piece is added the moment it arrives: the reply "types itself".
            update(reply(), (message) => ({ ...message, text: message.text + event.delta }))
            break
          case "TOOL_CALL_START": {
            const tool: ToolActivity = { id: event.toolCallId, name: event.toolCallName, args: "", status: "running" }
            update(reply(), (message) => ({ ...message, tools: [...(message.tools ?? []), tool] }))
            break
          }
          case "TOOL_CALL_ARGS":
            updateTool(event.toolCallId, (tool) => ({ ...tool, args: tool.args + event.delta }))
            break
          // TOOL_CALL_END only says the arguments are complete; the chip keeps spinning while the tool runs.
          case "TOOL_CALL_RESULT":
            updateTool(event.toolCallId, (tool) => ({
              ...tool,
              status: event.metadata?.ok === false ? "failed" : "done",
              result: event.content,
            }))
            break
          case "STATE_SNAPSHOT":
            // A tool changed expenses. A new dataVersion makes every page that shows them reload.
            setDataVersion(event.snapshot.dataVersion)
            break
          case "CUSTOM":
            // A2UI rides in AG-UI's extension event. Custom events with other names are ignored.
            if (event.name === "a2ui") {
              update(reply(), (message) => ({ ...message, surfaces: applyA2uiMessage(message.surfaces ?? [], event.value) }))
            }
            break
        }
      })
      return true
    } catch (error) {
      // The run failed: a tool still spinning will never finish, so don't leave it spinning.
      update(replyId, (message) => ({
        ...message,
        tools: message.tools?.map((tool) => (tool.status === "running" ? { ...tool, status: "failed" } : tool)),
      }))
      // Any text that already arrived stays; the error appears as its own red bubble below it.
      add({ role: "assistant", text: error instanceof Error ? error.message : String(error), failed: true })
      return false
    } finally {
      setSending(false)
    }
  }

  // Forget the conversation; the next message starts a new thread on the server.
  function reset() {
    setMessages([])
    setThreadId(null)
  }

  return { messages, threadId, sending, send, setFormValue, submitForm, reset }
}

export type ChatState = ReturnType<typeof useChat>
