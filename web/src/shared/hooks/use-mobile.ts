// A shared hook: whether the window is phone-sized. Part of shared/hooks. Used by app/layout (the chat becomes a
// sliding sheet) and by shadcn's Sidebar in shared/ui (it becomes a slide-in menu), which imports it by this path.

import { useSyncExternalStore } from "react"

// Narrower than this many pixels counts as a phone (Tailwind's `md` breakpoint starts here).
const MOBILE_BREAKPOINT = 768
const MOBILE_QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

// How useSyncExternalStore listens: call `onChange` whenever the media query's answer flips. Returns the unsubscribe.
function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(MOBILE_QUERY)
  query.addEventListener("change", onChange)
  return () => query.removeEventListener("change", onChange)
}

/**
 * Whether the window is phone-sized, kept up to date as it's resized. useSyncExternalStore is React's
 * way to read something outside React: the first render already has the real answer (no desktop
 * layout drawn and then replaced), and there's no setState inside an effect.
 */
export function useIsMobile(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia(MOBILE_QUERY).matches)
}
