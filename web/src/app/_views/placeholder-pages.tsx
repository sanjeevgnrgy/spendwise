// The placeholder page: "Page not found". Part of the app composition (app/). Used by the root not-found.tsx, through
// client-pages.ts. A component, so its texts are looked up when it's drawn, in the language on then.

import { PlaceholderPage } from "@/shared/components/placeholder-page"

import { useTexts } from "../_i18n"

/** What an address with no page shows. */
export function NotFoundPage() {
  const { t } = useTexts()
  return <PlaceholderPage title={t("notFound.title")} description={t("notFound.description")} />
}
