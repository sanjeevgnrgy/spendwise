// The Settings page (/settings): the signed-in person's profile, where they're signed in, and their access tokens.
// Part of the account feature (components/), the feature's page; its route file is
// app/(client)/(app)/settings/page.tsx. Everything on it is the person's own: the server answers each list for the
// session's owner only (D190).

import { useTexts } from "../i18n"
import { ProfileCard } from "./profile-card"
import { SessionsCard } from "./sessions/sessions-card"
import { TokensCard } from "./tokens/tokens-card"

/** The page: a heading, then one card per section. Each list loads, fails and refreshes on its own. */
export function SettingsPage() {
  const { t } = useTexts()
  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">{t("page.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("page.description")}</p>
      </div>
      <ProfileCard />
      <SessionsCard />
      <TokensCard />
    </div>
  )
}
