import { MessageSquare } from "lucide-react"
import { useState } from "react"
import { Outlet } from "react-router"

import { AppSidebar } from "@/components/app-sidebar"
import { ChatPanel } from "@/components/chat/chat-panel"
import { ModeToggle } from "@/components/mode-toggle"
import { Button } from "@/components/ui/button"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { useChat } from "@/hooks/use-chat"
import { useIsMobile } from "@/hooks/use-mobile"

// The frame around every page: sidebar on the left, a top bar, the current page, and the
// assistant's chat panel on the right (a Sheet that slides in, on small screens).
export function AppLayout() {
  const [chatOpen, setChatOpen] = useState(false)
  // The conversation lives here, in the layout that stays on screen across pages, not in the panel.
  const chat = useChat()
  const isMobile = useIsMobile()

  const panel = <ChatPanel chat={chat} onClose={() => setChatOpen(false)} />

  return (
    <SidebarProvider>
      <AppSidebar />
      {/* h-svh + overflow-hidden: the page and the chat scroll separately, inside the window. */}
      <SidebarInset className="h-svh overflow-hidden">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="mx-1 h-4" />
          <span className="font-medium">SpendWise</span>
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
              <Outlet />
            </div>
            <Sheet open={chatOpen} onOpenChange={setChatOpen}>
              <SheetContent side="right" showCloseButton={false} className="w-full gap-0 p-0 sm:max-w-md">
                {/* Screen readers need a title for the sheet; the panel shows its own visible header. */}
                <SheetHeader className="sr-only">
                  <SheetTitle>Assistant</SheetTitle>
                  <SheetDescription>Chat with the SpendWise assistant.</SheetDescription>
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
                {/* <Outlet /> is where the router puts the page that matches the URL. */}
                <Outlet />
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
