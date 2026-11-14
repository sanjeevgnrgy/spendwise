// The frame around every page: the sidebar, the top bar (sidebar toggle, app name, Assistant button, theme menu),
// the page area, and the assistant's chat panel. Part of the app composition (app/layout/). app.tsx uses it as the
// layout route, so the router draws the current page inside it. The page area and the chat panel each get their
// own error boundary, so a crash in one leaves the other working.

import { MessageSquare } from "lucide-react"
import { Suspense, useState } from "react"
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

// The page that matches the URL (<Outlet /> is where the router puts it). If it crashes while drawing, only the
// page area shows the error; the sidebar, the top bar and the assistant keep working. A new address starts afresh:
// the boundary is keyed by the address, and a new key gives a new boundary with no error in it.
// Pages are loaded on first use (each feature's index.ts makes them lazy), so the page area waits in a Suspense
// with an empty fallback: the area stays blank for the moment a page's code takes to arrive.
function Page() {
  const { pathname } = useLocation()
  return (
    <ErrorBoundary
      key={pathname}
      fallback={(error, reset) => <SectionError title="This page hit a problem" message={messageOf(error)} onRetry={reset} />}
    >
      <Suspense fallback={null}>
        <Outlet />
      </Suspense>
    </ErrorBoundary>
  )
}

interface TopBarProps {
  // The chat panel is open: the Assistant button shows as pressed.
  chatOpen: boolean
  // The Assistant button was pressed: open the chat if it's closed, close it if it's open.
  onToggleChat: () => void
}

// The bar across the top: the sidebar toggle, the app's name, the Assistant button and the theme menu.
function TopBar({ chatOpen, onToggleChat }: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger />
      <Separator orientation="vertical" className="mx-1 h-4" />
      <span className="font-medium">{APP_NAME}</span>
      <div className="ml-auto flex items-center gap-1">
        <Button variant={chatOpen ? "secondary" : "ghost"} size="sm" onClick={onToggleChat} aria-pressed={chatOpen}>
          <MessageSquare /> Assistant
        </Button>
        <ModeToggle />
      </div>
    </header>
  )
}

/**
 * The frame around every page: sidebar on the left, a top bar, the current page, and the
 * assistant's chat panel on the right (a Sheet that slides in, on small screens).
 * On wider windows the chat is a resizable panel beside the page, there only while it's open. The top bar's
 * Assistant button opens and closes it; the panel's own close button closes it.
 */
export function AppLayout() {
  // The chat starts closed. Only its panel closes: the conversation itself lives in AssistantProvider (providers.tsx).
  const [chatOpen, setChatOpen] = useState(false)
  const isMobile = useIsMobile()

  // The chat has its own safety net: if it crashes, the pages keep working (and vice versa).
  // Built once here, then placed in whichever container suits the window (the Sheet or the side panel).
  const panel = (
    <ErrorBoundary
      fallback={(error, reset) => <SectionError title="The assistant hit a problem" message={messageOf(error)} onRetry={reset} />}
    >
      <ChatPanel onClose={() => setChatOpen(false)} />
    </ErrorBoundary>
  )

  // h-svh + overflow-hidden on the inset: the page and the chat scroll separately, inside the window. The Sheet
  // gets a title for screen readers only (the panel shows its own visible header). The resizable panels' ids let
  // the group add and remove the chat panel without remounting the page; their sizes are strings, which mean
  // percentages (plain numbers would mean pixels).
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="h-svh overflow-hidden">
        <TopBar chatOpen={chatOpen} onToggleChat={() => setChatOpen((open) => !open)} />

        {isMobile ? (
          <>
            <div className="min-h-0 flex-1 overflow-auto p-4">
              <Page />
            </div>
            <Sheet open={chatOpen} onOpenChange={setChatOpen}>
              <SheetContent side="right" showCloseButton={false} className="w-full gap-0 p-0 sm:max-w-md">
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
            <ResizablePanel id="page" minSize="40%">
              <div className="h-full overflow-auto p-4 md:p-6">
                <Page />
              </div>
            </ResizablePanel>
            {chatOpen && (
              <>
                <ResizableHandle withHandle />
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
