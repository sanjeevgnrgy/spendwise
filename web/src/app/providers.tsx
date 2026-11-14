// The providers: app-wide services that any component below them can reach through React context. Part of the
// app composition (app/). It's also where the assistant meets the app's refresh rule: when the assistant reports
// that data changed, refreshAfter (query-client.ts) runs for expenses, so the assistant feature never needs to know
// which pages show expenses. Used once, by main.tsx, around <App />.

import { QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { BrowserRouter } from "react-router"

import { AssistantProvider } from "@/features/assistant"
import { DATA_SCOPES } from "@/shared/config/data-scopes"
import { ThemeProvider } from "@/shared/theme"
import { Toaster } from "@/shared/ui/sonner"
import { TooltipProvider } from "@/shared/ui/tooltip"

import { queryClient, refreshAfter } from "./query-client"

// When the assistant changes expenses, the same rule as for the app's own changes applies.
// A plain function made once, outside the component: all it needs is the app's one queryClient.
const refreshAfterAssistant = () => refreshAfter(queryClient, DATA_SCOPES.expenses)

/**
 * Everything the whole app shares: server data (TanStack Query), the theme, tooltips (used by the
 * collapsed sidebar), the router (current URL), the assistant's conversation, and toast messages.
 * The conversation lives here, above the pages, so it survives moving between pages and closing the chat panel.
 * The Toaster is the one place where toast messages appear, for every page.
 */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <BrowserRouter>
            <AssistantProvider onDataChanged={refreshAfterAssistant}>{children}</AssistantProvider>
          </BrowserRouter>
          <Toaster position="top-right" richColors />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
