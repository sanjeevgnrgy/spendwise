// The React context that carries the conversation (ChatState) from AssistantProvider down to this feature's
// components, and `useAssistant()` to read it. Used by the chat panel; the provider fills it.

import { createContext, useContext } from "react"

import type { ChatState } from "./chat-types"

/**
 * The conversation, for any component of this feature. It lives in a provider above the pages, so closing the
 * panel or changing page keeps the chat.
 */
export const AssistantContext = createContext<ChatState | null>(null)

/** The conversation from the nearest AssistantProvider. Throws if there is none (a wiring mistake). */
export function useAssistant(): ChatState {
  const context = useContext(AssistantContext)
  if (!context) throw new Error("useAssistant must be used inside <AssistantProvider>")
  return context
}
