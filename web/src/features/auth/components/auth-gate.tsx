// The session check in front of every signed-in page. Part of the auth feature (components/); the signed-in pages'
// layout (app/(client)/(app)/layout.tsx) draws the frame and the page inside it. The server is what protects the data
// (every API call needs the session, and every row has its owner, D186, D190); this only decides what to show, and
// makes sure a page never goes on showing one person's data to another (use-session-boundary.ts).

import type { ReactNode } from "react"

import { messageOf } from "@/shared/lib/errors"

import { useSignedInUser } from "../queries"
import { useSessionBoundary } from "../use-session-boundary"
import { SessionCheckFailed, SessionChecking } from "./session-screens"

/**
 * Draws `children` for a signed-in person. Nobody signed in: off to the sign-in page, which remembers this address so
 * signing in comes back here. While asking (or leaving), a spinner; if asking failed (the backend unreachable), a
 * "try again". A user already known is kept on screen while the answer is checked again (a refocus, a 401 elsewhere),
 * unless the answer is someone else: then the page reloads for them.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const user = useSignedInUser()
  const leaving = useSessionBoundary(user.data)

  if (user.data && !leaving) return children
  if (user.isError && user.data === undefined) {
    return (
      <SessionCheckFailed message={messageOf(user.error)} onRetry={() => user.refetch()} retrying={user.isFetching} />
    )
  }
  return <SessionChecking />
}
