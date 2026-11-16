// What search engines may crawl: /robots.txt, served by Next.js from this file. Part of the app composition (app/).
// Only the public pages (today, the sign-in page); the signed-in pages and the API are off limits, since a crawler
// never signs in (D188). The sitemap's address comes from the same site URL (seo.ts).

import type { MetadataRoute } from "next"

import { API_PREFIX } from "@/shared/api/contracts.gen"

import { PUBLIC_PATHS, siteUrl } from "./_seo/seo"

// "Everything" in a robots.txt rule: a crawler reads the most specific matching rule, so Allow beats it.
const EVERYTHING = "/"

/** robots.txt: the public pages may be crawled; everything else, the API included, may not. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: [...PUBLIC_PATHS], disallow: [EVERYTHING, `${API_PREFIX}/`] },
    sitemap: new URL("/sitemap.xml", siteUrl()).toString(),
  }
}
