"use client"

// The browser-side app's root: it starts i18next with the boot namespaces, then draws the outermost error boundary,
// the shared providers and the page. Part of the app composition (app/). The (client) route group's layout renders
// it around every page (D188). Until the texts are in it draws nothing, on the server too, so code that needs the
// browser (the saved language and theme, the window's width) only ever runs there, and the first paint is already in
// the right language.

import { useEffect, useState, type ReactNode } from "react"

import { ErrorBoundary } from "@/shared/components/error-boundary"
import { initI18n } from "@/shared/i18n"

import { AppCrashed } from "./app-crashed"
import { BOOT_NAMESPACES } from "./namespaces"
import { Providers } from "./providers"

// Started once per page load, however often the root mounts (React's development checks mount it twice). If the
// chosen language can't be loaded, initI18n starts in English; if even that fails, the app draws anyway: the error
// goes to the console, and whatever can be drawn beats a blank window.
let booting: Promise<void> | undefined

function bootTexts(): Promise<void> {
  booting ??= initI18n(BOOT_NAMESPACES).catch((error: unknown) => console.error(error))
  return booting
}

// Whether the boot texts are in: false on the server and on the first render, true once initI18n has finished.
function useTextsReady(): boolean {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let live = true
    void bootTexts().then(() => live && setReady(true))
    return () => {
      live = false
    }
  }, [])
  return ready
}

/**
 * Everything browser-side, around `children` (the page). The outermost safety net (AppCrashed) catches a crash
 * outside the page area and the chat, which have boundaries of their own.
 */
export function ClientRoot({ children }: { children: ReactNode }) {
  const ready = useTextsReady()
  if (!ready) return null
  return (
    <ErrorBoundary fallback={(error) => <AppCrashed error={error} />}>
      <Providers>{children}</Providers>
    </ErrorBoundary>
  )
}
