import { QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { BrowserRouter } from "react-router"

import { AssistantProvider } from "@/features/assistant"
import { ThemeProvider } from "@/shared/theme"
import { Toaster } from "@/shared/ui/sonner"
import { TooltipProvider } from "@/shared/ui/tooltip"

import { queryClient, refreshExpenseData } from "./query-client"

// When the assistant changes expenses, the same rule as for the app's own changes applies.
const refreshAfterAssistant = () => refreshExpenseData(queryClient)

// Everything the whole app shares: server data (TanStack Query), the theme, tooltips (used by the
// collapsed sidebar), the router (current URL), the assistant's conversation, and toast messages.
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <BrowserRouter>
            <AssistantProvider onDataChanged={refreshAfterAssistant}>{children}</AssistantProvider>
          </BrowserRouter>
          {/* One place where toast messages appear, for every page. */}
          <Toaster position="top-right" richColors />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
