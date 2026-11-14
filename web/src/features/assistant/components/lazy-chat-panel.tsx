// The chat panel, loaded as its own chunk: the panel, the A2UI renderer and the chart code it draws with aren't
// needed for the first page, and the panel starts closed. Its texts ("assistant") load together with its code.
// Public as `ChatPanel` (index.ts), with the same props; app/layout uses it. AssistantProvider is not here: it stays
// in the main bundle, so the conversation exists before the panel's code arrives.

import { Suspense, useState, type ComponentType } from "react"

import { loadNamespaces } from "@/shared/i18n"
import { lazyWithRetry } from "@/shared/lib/lazy-with-retry"

import { assistantTexts } from "../i18n"
import type { ChatPanelProps } from "./chat-panel"

// Set as soon as the panel's code has arrived.
let loadedPanel: ComponentType<ChatPanelProps> | undefined

async function loadPanel(): Promise<{ default: ComponentType<ChatPanelProps> }> {
  const [{ ChatPanel }] = await Promise.all([import("./chat-panel"), loadNamespaces(assistantTexts)])
  loadedPanel = ChatPanel
  return { default: ChatPanel }
}

// Start loading when the app does, in the background, so opening the panel never waits for the network. If
// this early load fails (a network blip), it isn't an error yet: opening the panel tries once more.
const preloaded = loadPanel().catch(() => undefined)

// For a panel opened before its code has arrived. If that load fails too, the panel's error boundary shows it,
// and its "Try again" loads the code again (lazyWithRetry), with no page reload.
const PanelWhenLoaded = lazyWithRetry(async () => (await preloaded) ?? loadPanel())

/**
 * The chat panel (components/chat-panel.tsx), drawn from its separately loaded chunk; nothing shows until the
 * code is there.
 *
 * Usually the code arrived long before the panel is opened, and the panel is drawn directly. React.lazy is used
 * only otherwise, because a lazy component always suspends on its first draw, and React keeps a just-shown
 * fallback for at least 300 ms: the first opening would lag. The choice is made once per mount, so the
 * component type never switches under React (which would remount the panel and lose what's typed).
 */
export function LazyChatPanel(props: ChatPanelProps) {
  // An initialiser function: useState would call a component passed directly as if it were one.
  const [Panel] = useState<ComponentType<ChatPanelProps>>(() => loadedPanel ?? PanelWhenLoaded)
  return (
    <Suspense fallback={null}>
      <Panel {...props} />
    </Suspense>
  )
}
