// The Expenses page's route: "/expenses". Part of the app composition (app/). A server component for its metadata
// (privatePage: signed-in pages aren't indexed); the page itself is the expenses feature's, drawn in the browser.

import type { Metadata } from "next"

import en from "@/app/_i18n/en"
import { privatePage } from "@/app/_seo/seo"

import { ExpensesPage } from "@/app/_views/client-pages"

/** The tab's title, and kept out of search engines. */
export const metadata: Metadata = privatePage(en.pages.expenses)

/** The Expenses page. */
export default function Expenses() {
  return <ExpensesPage />
}
