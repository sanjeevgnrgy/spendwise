// The Budgets page's route: "/budgets", a page still to be built. Part of the app composition (app/). A server
// component for its metadata (privatePage); the placeholder is drawn in the browser.

import type { Metadata } from "next"

import en from "@/app/_i18n/en"
import { privatePage } from "@/app/_seo/seo"

import { ComingSoonPage } from "@/app/_views/client-pages"

/** The tab's title, and kept out of search engines. */
export const metadata: Metadata = privatePage(en.pages.budgets)

/** The Budgets placeholder. */
export default function Budgets() {
  return <ComingSoonPage name="budgets" />
}
