// The app's left-hand menu: the app's name and a link to every page. Part of the app composition (app/layout/),
// drawn by AppLayout. Its entries come from PAGES (pages.tsx), the same list the router uses. The sidebar's
// behaviour (collapsing, the slide-in version on phones, tooltips) comes from shadcn's Sidebar in shared/ui.

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

/**
 * The menu: one entry per page, the current one highlighted (its path equals the address exactly). When the
 * sidebar is collapsed to icons, hovering an entry shows its title as a tooltip. The rail along the sidebar's
 * edge (SidebarRail) collapses or expands it when clicked, like the top bar's toggle.
 */
export function AppSidebar() {
  const { pathname } = useLocation()

  // collapsible="icon": collapsing leaves a narrow strip of icons instead of hiding the menu. The entries are the
  // same list the router uses (pages.tsx), so a page and its menu entry can't drift apart. Each menu button renders
  // the router's link itself (asChild), with the menu button's styling.
  return (
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
              {PAGES.map((item) => (
                <SidebarMenuItem key={item.path}>
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
