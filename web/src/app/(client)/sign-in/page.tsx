// The sign-in page's route: "/sign-in". Part of the app composition (app/). A public page, so search engines may index
// it (publicPage: its own title and canonical address; robots.txt and the sitemap list it). The page itself is the
// auth feature's, drawn in the browser. It's lazy, and it reads the address's query (useSearchParams), which Next.js
// wants inside a Suspense boundary on a prerendered route; hence the Suspense.

import type { Metadata } from "next"
import { Suspense } from "react"

import en from "@/app/_i18n/en"
import { publicPage } from "@/app/_seo/seo"
import { SignInPage } from "@/app/_views/client-pages"
import { ROUTES } from "@/shared/config/routes"

/** The tab's title and the page's canonical address, for search engines. */
export const metadata: Metadata = publicPage(en.pages.signIn, ROUTES.signIn)

/** The sign-in page. */
export default function SignIn() {
  return (
    <Suspense fallback={null}>
      <SignInPage />
    </Suspense>
  )
}
