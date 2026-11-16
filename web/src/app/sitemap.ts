// The public pages' list for search engines: /sitemap.xml, served by Next.js from this file. Part of the app
// composition (app/). Today only the sign-in page is public; a landing page would join it (D188).

import type { MetadataRoute } from "next"

import { PUBLIC_PATHS, siteUrl } from "./_seo/seo"

/** sitemap.xml: every public page, at its full address. */
export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.map((path) => ({ url: new URL(path, siteUrl()).toString() }))
}
