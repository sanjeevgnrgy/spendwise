// The web app's entry point: index.html loads this module, and it draws the whole app into <div id="root">.
// Part of the app composition (app/). It first starts i18next with the boot namespaces (namespaces.ts), then, from
// the outside in, sets up React's StrictMode checks, the outermost error boundary, the shared providers
// (providers.tsx) and the routes (app.tsx). It also loads the global stylesheet (index.css). Nothing imports this file.

import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { ErrorBoundary } from "@/shared/components/error-boundary"
import { initI18n } from "@/shared/i18n"

import { App } from "./app"
import { AppCrashed } from "./app-crashed"
import "./index.css"
import { BOOT_NAMESPACES } from "./namespaces"
import { Providers } from "./providers"

// The element in index.html that the app is drawn into.
const ROOT_ELEMENT_ID = "root"

// index.html always has the root element, hence the `!` (TypeScript can't know that). StrictMode only acts in
// development: it draws components and runs effects twice, to bring out bugs early; a production build skips it.
// The outermost safety net (AppCrashed) catches a crash outside the page and the chat.
function render() {
  createRoot(document.getElementById(ROOT_ELEMENT_ID)!).render(
    <StrictMode>
      <ErrorBoundary fallback={(error) => <AppCrashed error={error} />}>
        <Providers>
          <App />
        </Providers>
      </ErrorBoundary>
    </StrictMode>,
  )
}

// Draw once the starting language's texts are in, so the first paint is already in that language. (If that language
// can't be loaded, initI18n starts in English.) If even that fails, draw anyway: the error goes to the console, and
// whatever can be drawn beats a blank window.
initI18n(BOOT_NAMESPACES)
  .catch((error: unknown) => console.error(error))
  .finally(render)
