// The app's left-hand menu: the app's name and a link to every page. Part of the app composition (app/_frame/),
// drawn by AppLayout. Its entries come from PAGES (pages.tsx), the same list the router uses. The sidebar's
// behaviour (collapsing, the slide-in version on phones, tooltips) comes from shadcn's Sidebar in shared/ui.

import { Wallet } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

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

import { useTexts } from "../_i18n"
import { PAGES } from "./pages"

/**
 * The menu: one entry per page, the current one highlighted (its path equals the address exactly), each named in
 * the language on now. When the sidebar is collapsed to icons, hovering an entry shows its name as a tooltip. The
 * rail along the sidebar's edge (SidebarRail) collapses or expands it when clicked, like the top bar's toggle.
 */
export function AppSidebar() {
  const pathname = usePathname()
  const { t } = useTexts()

  // collapsible="icon": collapsing leaves a narrow strip of icons instead of hiding the menu. The entries are the
  // same list as the routes (pages.tsx), so a page and its menu entry can't drift apart. Each menu button renders
  // Next's link itself (asChild), with the menu button's styling.
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
          <SidebarGroupLabel>{t("menu")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {PAGES.map((item) => (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton asChild isActive={pathname === item.path} tooltip={t(`pages.${item.name}`)}>
                    <Link href={item.path}>
                      <item.icon />
                      <span>{t(`pages.${item.name}`)}</span>
                    </Link>
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
