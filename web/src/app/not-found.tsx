// What an address with no page shows: Next.js's root not-found page. Part of the app composition (app/). Next.js
// decides an address matches no route before it renders anything, so this always answers with a 404 status and a
// noindex tag for search engines (D188). The text is drawn in the browser, in the language on now, by the same
// client root as every other page.

import type { Metadata } from "next"

import { NotFoundPage } from "./_views/client-pages"
import { ClientRoot } from "./_shell/client-root"
import en from "./_i18n/en"

/** The tab's title (Next.js adds "noindex" to every 404 itself). */
export const metadata: Metadata = { title: en.notFound.title }

/** "Page not found", on its own: no frame, since it isn't a page of the app. */
export default function NotFound() {
  return (
    <ClientRoot>
      <main className="p-4 md:p-6">
        <NotFoundPage />
      </main>
    </ClientRoot>
  )
}
