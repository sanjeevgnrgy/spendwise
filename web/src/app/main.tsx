// The web app's entry point: index.html loads this module, and it draws the whole app into <div id="root">.
// Part of the app composition (app/). From the outside in, it sets up React's StrictMode checks, the outermost
// error boundary, the shared providers (providers.tsx) and the routes (app.tsx), and it loads the global
// stylesheet (index.css). Nothing imports this file.

import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { ErrorBoundary } from "@/shared/components/error-boundary"
import { SectionError } from "@/shared/components/section-error"
import { APP_NAME } from "@/shared/config/app"
import { messageOf } from "@/shared/lib/errors"

import { App } from "./app"
import "./index.css"
import { Providers } from "./providers"

// The element in index.html that the app is drawn into.
const ROOT_ELEMENT_ID = "root"

// The outermost safety net: if something outside the page and the chat crashes (the sidebar, a provider),
// show what happened and a way back, instead of a blank window. "Try again" reloads the whole window, which
// starts every provider afresh, rather than redrawing the same broken tree.
const crashed = (error: Error) => (
  <div className="p-6">
    <SectionError title={`${APP_NAME} hit a problem`} message={messageOf(error)} onRetry={() => window.location.reload()} />
  </div>
)

// index.html always has the root element, hence the `!` (TypeScript can't know that). StrictMode only acts in
// development: it draws components and runs effects twice, to bring out bugs early; a production build skips it.
createRoot(document.getElementById(ROOT_ELEMENT_ID)!).render(
  <StrictMode>
    <ErrorBoundary fallback={crashed}>
      <Providers>
        <App />
      </Providers>
    </ErrorBoundary>
  </StrictMode>,
)
