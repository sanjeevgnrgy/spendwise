// Keeps this browser's tabs in step about who is signed in. Part of the auth feature; used by the session check
// (use-session-boundary.ts) and the sign-in page. Signing in or out happens in one tab, by navigation; the other tabs
// would go on showing the previous person's page until their own cached answer went stale. So each page, when it first
// learns who is signed in, tells the others that the answer may have changed, and they ask the server again.
//
// The message carries nothing and is never trusted: it only means "ask again". What a tab then does depends on the
// server's answer alone (stay, reload for the new person, or go to the sign-in page).

import { useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"

import { authKeys } from "./queries"

// The channel's name, and its one message (any message means the same).
const SESSION_CHANNEL = "spendwise-session"
const ASK_AGAIN = "ask-again"

/**
 * Listens for other tabs' "who is signed in may have changed", asking the server again when one arrives, and sends
 * that message once itself, when `known` turns true (this page has its first answer). Does nothing in a browser
 * without BroadcastChannel: there, a tab catches up at its next 401 or when its answer goes stale.
 */
export function useSessionSync(known: boolean): void {
  const client = useQueryClient()
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return
    // One channel for both directions: a channel never hears its own message, so this page doesn't ask twice.
    const channel = new BroadcastChannel(SESSION_CHANNEL)
    channel.onmessage = () => void client.invalidateQueries({ queryKey: authKeys.user })
    if (known) channel.postMessage(ASK_AGAIN)
    return () => channel.close()
  }, [client, known])
}
