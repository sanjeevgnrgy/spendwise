import { Outlet } from "react-router"

import { AppSidebar } from "@/components/app-sidebar"
import { ModeToggle } from "@/components/mode-toggle"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"

// The frame around every page: sidebar on the left, a top bar, and the current page below it.
export function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="mx-1 h-4" />
          <span className="font-medium">SpendWise</span>
          <div className="ml-auto">
            <ModeToggle />
          </div>
        </header>
        <main className="flex-1 p-4 md:p-6">
          {/* <Outlet /> is where the router puts the page that matches the URL. */}
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
