// The auth feature's public API: the app imports ONLY from "@/features/auth".
// - AuthGate: the session check in front of every signed-in page (app/(client)/(app)/layout.tsx).
// - SignInPage: the sign-in page (its route file draws it), loaded on first use.
// - UserMenu: the top bar's account menu with Sign out (app/_frame/app-layout.tsx).
// - authTexts: the feature's texts, loaded at boot (app/_shell/namespaces.ts): the gate and the menu are in the frame.
// - authKeys, isSignedOut: so the app's query client can ask again who is signed in after any 401.
// - useSignedInUser, UserAvatar: who is signed in and their picture, for the Settings page's profile (account feature).

import { lazyWithRetry } from "@/shared/lib/lazy-with-retry"

export { isSignedOut } from "./api"
export { AuthGate } from "./components/auth-gate"
export { UserAvatar } from "./components/user-avatar"
export { UserMenu } from "./components/user-menu"
export { authTexts } from "./i18n"
export { authKeys, useSignedInUser } from "./queries"

/**
 * The sign-in page, loaded only when it's first shown (its texts are already in: they load at boot). Draw it inside a
 * <Suspense> (its route file does). If its code fails to load, the root error boundary shows it.
 */
export const SignInPage = lazyWithRetry(async () => {
  const { SignInPage: page } = await import("./components/sign-in-page")
  return { default: page }
})
