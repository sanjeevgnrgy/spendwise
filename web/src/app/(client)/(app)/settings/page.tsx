// The Settings page's route: "/settings". Part of the app composition (app/). A server component for its metadata
// (privatePage); the page itself is the account feature's (the person's profile, sessions and access tokens), drawn in
// the browser, behind the session check like every route in this group.

import type { Metadata } from "next"

import en from "@/app/_i18n/en"
import { privatePage } from "@/app/_seo/seo"

import { SettingsPage } from "@/app/_views/client-pages"

/** The tab's title, and kept out of search engines. */
export const metadata: Metadata = privatePage(en.pages.settings)

/** The Settings page. */
export default function Settings() {
  return <SettingsPage />
}
