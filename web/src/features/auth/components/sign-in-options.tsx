// The sign-in page's buttons: one per way of signing in the server offers ("Continue with Google"), or a single "Sign
// in" that opens the provider's own page. Part of the auth feature (components/). Used by sign-in-page.tsx. Each button
// is a link: signing in is a navigation to the backend, which sends the browser on to the provider.

import { Button } from "@/shared/ui/button"
import { Skeleton } from "@/shared/ui/skeleton"

import type { LoginOption } from "../api"
import { useTexts } from "../i18n"
import { loginUrl } from "../sign-in-urls"

// How many placeholder buttons show while the options load (most setups offer one or two).
const PLACEHOLDER_BUTTONS = 2

interface SignInOptionsProps {
  /** The server's ways to sign in; undefined while they load (placeholders show), [] for the provider's own page. */
  options: LoginOption[] | undefined
  /** The page to come back to (the server checks it). */
  returnTo: string | null
}

/** The ways to sign in, each a link to the backend's login route. */
export function SignInOptions({ options, returnTo }: SignInOptionsProps) {
  const { t } = useTexts()
  if (options === undefined) {
    return (
      // <output> is announced politely by screen readers (its role is "status").
      <output className="grid gap-3">
        <span className="sr-only">{t("signIn.loadingOptions")}</span>
        {Array.from({ length: PLACEHOLDER_BUTTONS }, (_, index) => (
          <Skeleton key={index} className="h-10 w-full" />
        ))}
      </output>
    )
  }
  if (options.length === 0) {
    return (
      <Button asChild size="lg">
        <a href={loginUrl(undefined, returnTo)}>{t("signIn.signIn")}</a>
      </Button>
    )
  }
  return (
    <div className="grid gap-3">
      {options.map((option) => (
        <Button key={option.key} asChild size="lg" variant="outline">
          <a href={loginUrl(option.key, returnTo)}>{t("signIn.continueWith", { provider: option.label })}</a>
        </Button>
      ))}
    </div>
  )
}
