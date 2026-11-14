// The assistant feature's public API: the app imports ONLY from "@/features/assistant". `ChatPanel` is the lazily
// loaded panel (its code arrives as a separate chunk); `AssistantProvider` holds the conversation and stays in the
// main bundle. The panel's texts load with its code (lazy-chat-panel.tsx).

export { LazyChatPanel as ChatPanel } from "./components/lazy-chat-panel"
export { AssistantProvider } from "./model/assistant-provider"
