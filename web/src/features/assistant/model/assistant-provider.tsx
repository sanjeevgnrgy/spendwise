// Holds the assistant conversation above the pages, so it survives closing the panel and changing page. Public
// (index.ts): app/providers.tsx wraps the app in it and decides what `onDataChanged` reloads. It stays in the
// main bundle; only the panel's code is loaded separately (components/lazy-chat-panel.tsx).

import { useCallback, useEffect, useRef, type ReactNode } from "react"

import { AssistantContext } from "./assistant-context"
import { useChat } from "./use-chat"

interface AssistantProviderProps {
  /**
   * Called when the assistant may have changed expenses. The app decides what to reload; this feature doesn't
   * know which pages exist.
   */
  onDataChanged: () => void
  children: ReactNode
}

/** Runs the conversation (useChat) and shares it with this feature's components through AssistantContext. */
export function AssistantProvider({ onDataChanged, children }: AssistantProviderProps) {
  // Always call the newest callback, even from a run that started before it changed.
  const latest = useRef(onDataChanged)
  useEffect(() => {
    latest.current = onDataChanged
  }, [onDataChanged])

  // One function for the provider's lifetime, so useChat's callbacks (and the memoised bubbles) stay stable.
  const dataChanged = useCallback(() => latest.current(), [])
  const chat = useChat(dataChanged)
  return <AssistantContext value={chat}>{children}</AssistantContext>
}
