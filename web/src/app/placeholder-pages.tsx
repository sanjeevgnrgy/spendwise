// The pages that are only placeholders: one still to be built, and "Page not found". Part of the app composition
// (app/). Used by pages.tsx. Components, so their texts are looked up when they're drawn, in the language on then.

import { PlaceholderPage } from "@/shared/components/placeholder-page"

import { useTexts, type ComingSoonName } from "./i18n"

/** A page that isn't built yet: its name as the heading, and its "comingSoon" text under "Coming soon". */
export function ComingSoonPage({ name }: { name: ComingSoonName }) {
  const { t } = useTexts()
  return <PlaceholderPage title={t(`pages.${name}`)} description={t(`comingSoon.${name}`)} />
}

/** What an address with no page shows. */
export function NotFoundPage() {
  const { t } = useTexts()
  return <PlaceholderPage title={t("notFound.title")} description={t("notFound.description")} />
}
