import { useRef, useState } from "react"

import { sendChatMessage, type ToolCall } from "@/api"
import { useDataSync } from "@/lib/data-sync"

export interface ChatMessage {
  id: number
  role: "user" | "assistant"
  text: string
  toolCalls?: ToolCall[]
  failed?: boolean // the request itself failed; text is the error
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

  function add(message: Omit<ChatMessage, "id">) {
    const id = nextId.current++
    setMessages((current) => [...current, { ...message, id }])
  }

  async function send(text: string) {
    add({ role: "user", text })
    setSending(true)
    try {
      const reply = await sendChatMessage(text, threadId ?? undefined)
      setThreadId(reply.thread_id)
      add({ role: "assistant", text: reply.reply, toolCalls: reply.tool_calls })
      // The assistant changed expenses: tell every page showing them to reload.
      if (changedData(reply.tool_calls)) notifyDataChanged()
    } catch (error) {
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
