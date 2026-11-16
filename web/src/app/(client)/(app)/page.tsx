// The Dashboard's route: "/". Part of the app composition (app/). A server component, so it can say what the browser
// tab and search engines are told (privatePage: signed-in pages aren't indexed); the page itself is the dashboard
// feature's, drawn in the browser.

import type { Metadata } from "next"

import en from "@/app/_i18n/en"
import { privatePage } from "@/app/_seo/seo"

import { DashboardPage } from "@/app/_views/client-pages"

/** The tab's title, and kept out of search engines. */
export const metadata: Metadata = privatePage(en.pages.dashboard)

/** The Dashboard page. */
export default function Dashboard() {
  return <DashboardPage />
}
