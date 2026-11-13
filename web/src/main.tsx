import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router"

import App from "@/App"
import { DataSyncProvider } from "@/components/data-sync-provider"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./index.css"

// Providers wrap the whole app so any component can use what they provide: the theme
// (light/dark), the shared data version (chat -> pages), tooltips (used by the collapsed sidebar)
// and the router (current URL).
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <DataSyncProvider>
        <TooltipProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
          {/* One place where toast messages appear, for every page. */}
          <Toaster position="top-right" richColors />
        </TooltipProvider>
      </DataSyncProvider>
    </ThemeProvider>
  </StrictMode>,
)
