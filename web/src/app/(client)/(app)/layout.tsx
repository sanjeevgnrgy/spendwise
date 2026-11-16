"use client"

// The layout of every signed-in page (the "(app)" route group): the session check, then the frame (sidebar, top bar,
// chat panel) around the page. Part of the app composition (app/). Pages outside the group, like the sign-in page, are
// drawn without either.

import type { ReactNode } from "react"

import { AppLayout } from "@/app/_frame/app-layout"
import { AuthGate } from "@/features/auth"

/** The page in the app's frame, for a signed-in person; anyone else is sent to the sign-in page. */
export default function SignedInLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <AppLayout>{children}</AppLayout>
    </AuthGate>
  )
}
