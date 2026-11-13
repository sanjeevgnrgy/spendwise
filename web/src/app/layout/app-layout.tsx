import { MessageSquare } from "lucide-react"
import { useState } from "react"
import { Outlet, useLocation } from "react-router"

import { ChatPanel } from "@/features/assistant"
import { ErrorBoundary } from "@/shared/components/error-boundary"
import { SectionError } from "@/shared/components/section-error"
import { useIsMobile } from "@/shared/hooks/use-mobile"
import { APP_NAME } from "@/shared/config/app"
import { messageOf } from "@/shared/lib/errors"
import { ModeToggle } from "@/shared/theme"
import { Button } from "@/shared/ui/button"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/shared/ui/resizable"
import { Separator } from "@/shared/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/shared/ui/sheet"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/shared/ui/sidebar"

import { AppSidebar } from "./app-sidebar"

// The page that matches the URL. If it crashes while drawing, only the page area shows the error;
// the sidebar, the top bar and the assistant keep working. A new address starts afresh.
function Page() {
  const { pathname } = useLocation()
  return (
    <ErrorBoundary
      key={pathname}
      fallback={(error, reset) => <SectionError title="This page hit a problem" message={messageOf(error)} onRetry={reset} />}
    >
      {/* <Outlet /> is where the router puts the page that matches the URL. */}
      <Outlet />
    </ErrorBoundary>
  )
}

// The frame around every page: sidebar on the left, a top bar, the current page, and the
// assistant's chat panel on the right (a Sheet that slides in, on small screens).
export function AppLayout() {
  const [chatOpen, setChatOpen] = useState(false)
  const isMobile = useIsMobile()

  // The chat has its own safety net: if it crashes, the pages keep working (and vice versa).
  const panel = (
    <ErrorBoundary
      fallback={(error, reset) => <SectionError title="The assistant hit a problem" message={messageOf(error)} onRetry={reset} />}
    >
      <ChatPanel onClose={() => setChatOpen(false)} />
    </ErrorBoundary>
  )

  return (
    <SidebarProvider>
      <AppSidebar />
      {/* h-svh + overflow-hidden: the page and the chat scroll separately, inside the window. */}
      <SidebarInset className="h-svh overflow-hidden">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="mx-1 h-4" />
          <span className="font-medium">{APP_NAME}</span>
          <div className="ml-auto flex items-center gap-1">
            <Button
              variant={chatOpen ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setChatOpen((open) => !open)}
              aria-pressed={chatOpen}
            >
              <MessageSquare /> Assistant
            </Button>
            <ModeToggle />
          </div>
        </header>

        {isMobile ? (
          <>
            <div className="min-h-0 flex-1 overflow-auto p-4">
              <Page />
            </div>
            <Sheet open={chatOpen} onOpenChange={setChatOpen}>
              <SheetContent side="right" showCloseButton={false} className="w-full gap-0 p-0 sm:max-w-md">
                {/* Screen readers need a title for the sheet; the panel shows its own visible header. */}
                <SheetHeader className="sr-only">
                  <SheetTitle>Assistant</SheetTitle>
                  <SheetDescription>Chat with the {APP_NAME} assistant.</SheetDescription>
                </SheetHeader>
                {panel}
              </SheetContent>
            </Sheet>
          </>
        ) : (
          <ResizablePanelGroup orientation="horizontal" className="min-h-0 flex-1">
            {/* The ids let the group add and remove the chat panel without remounting the page. */}
            <ResizablePanel id="page" minSize="40%">
              <div className="h-full overflow-auto p-4 md:p-6">
                <Page />
              </div>
            </ResizablePanel>
            {chatOpen && (
              <>
                <ResizableHandle withHandle />
                {/* Sizes as strings are percentages; plain numbers would mean pixels. */}
                <ResizablePanel id="chat" defaultSize="32%" minSize="22%" maxSize="50%">
                  {panel}
                </ResizablePanel>
              </>
            )}
          </ResizablePanelGroup>
        )}
      </SidebarInset>
    </SidebarProvider>
  )
}
