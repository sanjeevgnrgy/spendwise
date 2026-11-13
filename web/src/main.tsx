import { ThemeProvider } from "next-themes"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router"

import App from "@/App"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./index.css"

// Providers wrap the whole app so any component can use what they provide:
// the theme (light/dark), tooltips (used by the collapsed sidebar) and the router (current URL).
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {/* attribute="class": put "dark" on <html>, which is what index.css's dark colours key off. */}
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <TooltipProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
        {/* One place where toast messages appear, for every page. */}
        <Toaster position="top-right" richColors />
      </TooltipProvider>
    </ThemeProvider>
  </StrictMode>,
)
