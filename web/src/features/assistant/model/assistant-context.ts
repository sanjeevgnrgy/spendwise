import { createContext, useContext } from "react"

import type { ChatState } from "./use-chat"

// The conversation, for any component of this feature. It lives in a provider above the pages, so
// closing the panel or changing page keeps the chat.
export const AssistantContext = createContext<ChatState | null>(null)

export function useAssistant(): ChatState {
  const context = useContext(AssistantContext)
  if (!context) throw new Error("useAssistant must be used inside <AssistantProvider>")
  return context
}
