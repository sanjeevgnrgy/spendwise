// The layout of every page drawn in the browser (the "(client)" route group: the group's name isn't part of the
// URL). Part of the app composition (app/). It hands the page to ClientRoot, which boots the texts and the providers
// first (D188). Public pages that should be rendered on the server, like a landing page, can live outside the group.

import type { ReactNode } from "react"

import { ClientRoot } from "@/app/_shell/client-root"

/** The browser-side app around the page. */
export default function ClientLayout({ children }: { children: ReactNode }) {
  return <ClientRoot>{children}</ClientRoot>
}
