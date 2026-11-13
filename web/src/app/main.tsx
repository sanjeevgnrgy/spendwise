import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { ErrorBoundary } from "@/shared/components/error-boundary"
import { SectionError } from "@/shared/components/section-error"
import { APP_NAME } from "@/shared/config/app"
import { messageOf } from "@/shared/lib/errors"

import { App } from "./app"
import "./index.css"
import { Providers } from "./providers"

const ROOT_ELEMENT_ID = "root"

// The outermost safety net: if something outside the page and the chat crashes (the sidebar, a provider),
// show what happened and a way back, instead of a blank window.
const crashed = (error: Error) => (
  <div className="p-6">
    <SectionError title={`${APP_NAME} hit a problem`} message={messageOf(error)} onRetry={() => window.location.reload()} />
  </div>
)

createRoot(document.getElementById(ROOT_ELEMENT_ID)!).render(
  <StrictMode>
    <ErrorBoundary fallback={crashed}>
      <Providers>
        <App />
      </Providers>
    </ErrorBoundary>
  </StrictMode>,
)
