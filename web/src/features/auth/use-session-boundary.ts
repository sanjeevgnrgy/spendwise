// The rule for what happens to a page when the person behind it changes: it's unloaded. Part of the auth feature; used
// by the session check (components/auth-gate.tsx). A page that has shown one person's data holds it in memory (the
// query cache, the chat, half-typed forms), so it must never go on to serve anyone else (D190):
// - the session ended (expired, or signed out in another tab): a full navigation to the sign-in page, which drops
//   everything the page held;
// - someone else is now signed in (in another tab, with the same browser): the page reloads, and starts again for them.
// Only a page that never showed anyone's data moves to the sign-in page inside the app, without a reload.
// It hears of a change from its own requests (any 401 asks again who is signed in, app/_shell/query-client.ts) and
// from this browser's other tabs (use-session-sync.ts).

import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import type { SignedInUser } from "./api"
import { currentPath, signInPath } from "./sign-in-urls"
import { useSessionSync } from "./use-session-sync"

/**
 * Watches who is signed in (`user`: the person, null for nobody, undefined while it's asked) and leaves the page when
 * that changes. Returns true while the page must not show the person's content: it's leaving, or about to.
 */
export function useSessionBoundary(user: SignedInUser | null | undefined): boolean {
  const router = useRouter()
  useSessionSync(user !== undefined)
  // The person this page was first drawn for; it never changes afterwards (React's "adjust state during render").
  const [person, setPerson] = useState<number | undefined>(undefined)
  if (person === undefined && user) setPerson(user.id)
  const signedOut = user === null
  const replaced = person !== undefined && user != null && user.id !== person

  // In an effect, not during render: the address comes from the browser, and leaving is a side effect.
  useEffect(() => {
    if (replaced) {
      window.location.reload()
    } else if (signedOut) {
      const signIn = signInPath(currentPath(window.location))
      // A page that showed someone's data is unloaded; one that never did just moves on.
      if (person === undefined) router.replace(signIn)
      else window.location.replace(signIn)
    }
  }, [replaced, signedOut, person, router])

  return replaced || signedOut
}
