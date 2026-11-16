// The sign-in page (/sign-in): why the last sign-in failed, if it did, and the ways to sign in. Part of the auth
// feature (components/), the feature's page; its route file is app/(client)/sign-in/page.tsx. The provider's own login
// page does the signing in (Google, GitHub); this page only sends people there.

import { Wallet } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect } from "react"

import { AUTH } from "@/shared/api/contracts.gen"
import { SectionError } from "@/shared/components/section-error"
import { APP_NAME } from "@/shared/config/app"
import { LanguageMenu } from "@/shared/i18n"
import { messageOf } from "@/shared/lib/errors"
import { ModeToggle } from "@/shared/theme"
import { Card, CardContent, CardDescription, CardHeader } from "@/shared/ui/card"

import { useTexts } from "../i18n"
import { useLoginOptions, useSignedInUser } from "../queries"
import { afterSignIn, failureText } from "../sign-in-urls"
import { useSessionSync } from "../use-session-sync"
import { SignInOptions } from "./sign-in-options"

/**
 * The page. The address may say why the last sign-in failed (?error=, the server's code: a text from "failures") and
 * which page to come back to (?return_to=, passed on to the backend). Someone already signed in (or who signs in
 * in another tab) goes on to that page, or the start page.
 * If the ways to sign in can't be loaded, that takes the card's place, with Try again.
 */
export function SignInPage() {
  const { t } = useTexts()
  const params = useSearchParams()
  const router = useRouter()
  const user = useSignedInUser()
  // Another tab signing in moves this page on too (and this page, drawn after a sign-out, tells the other tabs).
  useSessionSync(user.data !== undefined)
  const options = useLoginOptions()
  const returnTo = params.get(AUTH.params.returnTo)
  const failure = failureText(params.get(AUTH.params.error))

  useEffect(() => {
    if (user.data) router.replace(afterSignIn(returnTo, window.location.origin))
  }, [user.data, returnTo, router])

  return (
    <main className="relative flex min-h-svh items-center justify-center p-4">
      <div className="absolute top-4 right-4 flex items-center gap-1">
        <LanguageMenu />
        <ModeToggle />
      </div>
      {options.isError ? (
        <div className="w-full max-w-sm">
          <SectionError
            title={t("signIn.optionsFailed")}
            message={messageOf(options.error)}
            onRetry={() => options.refetch()}
            retrying={options.isFetching}
          />
        </div>
      ) : (
        <Card className="w-full max-w-sm">
          <CardHeader className="items-center text-center">
            <Wallet aria-hidden className="mx-auto size-8" />
            <h1 className="text-xl font-semibold">{t("signIn.title", { app: APP_NAME })}</h1>
            <CardDescription>{t("signIn.description")}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {failure && (
              <p role="alert" className="rounded-md border border-destructive/40 px-3 py-2 text-sm text-destructive">
                {t(`failures.${failure}`, { app: APP_NAME })}
              </p>
            )}
            <SignInOptions options={options.data} returnTo={returnTo} />
          </CardContent>
        </Card>
      )}
    </main>
  )
}
