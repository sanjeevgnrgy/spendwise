import { LayoutDashboard, PiggyBank, ReceiptText, Settings, Wallet, type LucideIcon } from "lucide-react"
import { NavLink, useLocation } from "react-router"

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
} from "@/components/ui/sidebar"

interface NavItem {
  title: string
  path: string
  icon: LucideIcon
}

// One list drives the whole menu: adding a page later means adding one line here (and a route).
const NAV_ITEMS: NavItem[] = [
  { title: "Dashboard", path: "/", icon: LayoutDashboard },
  { title: "Expenses", path: "/expenses", icon: ReceiptText },
  { title: "Budgets", path: "/budgets", icon: PiggyBank },
  { title: "Settings", path: "/settings", icon: Settings },
]

export function AppSidebar() {
  const { pathname } = useLocation()

  return (
    // collapsible="icon": collapsing leaves a narrow strip of icons instead of hiding the menu.
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5 font-semibold">
          <Wallet className="size-5 shrink-0" />
          <span className="truncate group-data-[collapsible=icon]:hidden">SpendWise</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Menu</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => (
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
