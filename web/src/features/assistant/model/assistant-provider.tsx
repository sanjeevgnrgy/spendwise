import { useEffect, useRef, type ReactNode } from "react"

import { AssistantContext } from "./assistant-context"
import { useChat } from "./use-chat"

interface AssistantProviderProps {
  // Called when the assistant may have changed expenses. The app decides what to reload; this feature
  // doesn't know which pages exist.
  onDataChanged: () => void
  children: ReactNode
}

export function AssistantProvider({ onDataChanged, children }: AssistantProviderProps) {
  // Always call the newest callback, even from a run that started before it changed.
  const latest = useRef(onDataChanged)
  useEffect(() => {
    latest.current = onDataChanged
  }, [onDataChanged])

  const chat = useChat(() => latest.current())
  return <AssistantContext value={chat}>{children}</AssistantContext>
}
