// The top bar's account menu: who is signed in, and Sign out. Part of the auth feature (components/); the frame's top
// bar (app/_frame/app-layout.tsx) draws it. Signing out is a navigation to the server's logout link, which ends the
// session there and at the provider (D186), so the page unloads and nothing of the session stays in memory.

import { LogOut } from "lucide-react"

import { reportUnexpected } from "@/shared/lib/errors"
import { Button } from "@/shared/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu"

import { useTexts } from "../i18n"
import { useSignedInUser } from "../queries"
import { ownSitePath } from "../sign-in-urls"
import { UserAvatar } from "./user-avatar"

// For the browser console only (developers): the server sent a sign-out link that leaves this site.
const FOREIGN_SIGN_OUT_LINK = "The sign-out link isn't on this site, so it wasn't followed."

// Leaves for the server's sign-out link, which ends the session here and at the provider. The link is the server's
// answer, so it's followed only if it stays on this site; anything else is a bug worth reporting, never a navigation.
function signOut(logoutUrl: string): void {
  const path = ownSitePath(logoutUrl, window.location.origin)
  if (path) window.location.assign(path)
  else reportUnexpected(new Error(FOREIGN_SIGN_OUT_LINK))
}

/** The person's picture and name; opened, their email and Sign out. Nothing while nobody is signed in. */
export function UserMenu() {
  const { t } = useTexts()
  const user = useSignedInUser().data
  if (!user) return null
  const name = user.name ?? user.email ?? t("userMenu.you")

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" aria-label={t("userMenu.label", { name })}>
          <UserAvatar name={name} picture={user.avatar_url} />
          <span className="hidden max-w-32 truncate sm:inline">{name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <p className="text-xs text-muted-foreground">{t("userMenu.signedInAs")}</p>
          <p className="truncate font-medium">{name}</p>
          {user.email && user.email !== name && <p className="truncate text-xs text-muted-foreground">{user.email}</p>}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => signOut(user.logout_url)}>
          <LogOut /> {t("userMenu.signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
