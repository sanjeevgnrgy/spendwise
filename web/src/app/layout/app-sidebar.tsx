import { Wallet } from "lucide-react"
import { NavLink, useLocation } from "react-router"

import { APP_NAME } from "@/shared/config/app"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/shared/ui/sidebar"

import { PAGES } from "../pages"

export function AppSidebar() {
  const { pathname } = useLocation()

  return (
    // collapsible="icon": collapsing leaves a narrow strip of icons instead of hiding the menu.
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5 font-semibold">
          <Wallet className="size-5 shrink-0" />
          <span className="truncate group-data-[collapsible=icon]:hidden">{APP_NAME}</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Menu</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {/* The same list the router uses (pages.tsx): a page and its menu entry can't drift apart. */}
              {PAGES.map((item) => (
                <SidebarMenuItem key={item.path}>
                  {/* asChild: render our router link, but with the menu button's styling. */}
                  <SidebarMenuButton asChild isActive={pathname === item.path} tooltip={item.title}>
                    <NavLink to={item.path}>
                      <item.icon />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
