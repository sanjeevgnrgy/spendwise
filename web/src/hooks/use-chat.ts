import { useRef, useState } from "react"

import { newId, runAgent, type ToolCall } from "@/api"
import { useDataSync } from "@/lib/data-sync"

export interface ChatMessage {
  id: number
  role: "user" | "assistant"
  text: string
  toolCalls?: ToolCall[]
  failed?: boolean // the run failed; text is the error
}

// Tools that change expenses. delete_expense only deletes with confirmed=true; without it,
// it just looks the expense up so the assistant can ask "are you sure?".
function changedData(toolCalls: ToolCall[]): boolean {
  return toolCalls.some(
    (call) =>
      call.ok &&
      (call.name === "add_expense" ||
        call.name === "update_expense" ||
        (call.name === "delete_expense" && call.arguments.confirmed === true)),
  )
}

// Everything about the conversation, as a custom hook. It's used by the layout (which stays on
// screen across pages), not by the panel, so closing the panel or changing page keeps the chat.
export function useChat() {
  const { notifyDataChanged } = useDataSync()
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

  async function send(text: string) {
    add({ role: "user", text })
    setSending(true)
    // With AG-UI the client names the thread; the server starts it when the first message arrives.
    const thread = threadId ?? newId()
    setThreadId(thread)
    let replyId: number | null = null
    try {
      await runAgent(thread, text, (event) => {
        switch (event.type) {
          case "TEXT_MESSAGE_START":
            replyId = add({ role: "assistant", text: "" })
            break
          case "TEXT_MESSAGE_CONTENT":
            // Each piece is added to the bubble the moment it arrives: the reply "types itself".
            update(replyId, (message) => ({ ...message, text: message.text + event.delta }))
            break
          case "RUN_FINISHED": {
            const toolCalls = event.result?.toolCalls ?? []
            update(replyId, (message) => ({ ...message, toolCalls }))
            // The assistant changed expenses: tell every page showing them to reload.
            if (changedData(toolCalls)) notifyDataChanged()
            break
          }
        }
      })
    } catch (error) {
      // Any text that already arrived stays; the error appears as its own red bubble below it.
      add({ role: "assistant", text: error instanceof Error ? error.message : String(error), failed: true })
    } finally {
      setSending(false)
    }
  }

  // Forget the conversation; the next message starts a new thread on the server.
  function reset() {
    setMessages([])
    setThreadId(null)
  }

  return { messages, threadId, sending, send, reset }
}

export type ChatState = ReturnType<typeof useChat>
