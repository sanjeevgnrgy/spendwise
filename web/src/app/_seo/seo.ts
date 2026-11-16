// What search engines and link previews are told about each page: the site's address, the default title and
// description, and which pages may be indexed. Part of the app composition (app/), server side only: the root layout
// and every page.tsx build their `metadata` from here, and robots.ts and sitemap.ts use the same address and the same
// list of public pages (D188).

import type { Metadata } from "next"

import { APP_DESCRIPTION, APP_NAME } from "@/shared/config/app"
import { ROUTES } from "@/shared/config/routes"
import { DEFAULT_PUBLIC_URL, PUBLIC_URL_SETTING } from "@/shared/config/site"

/**
 * The pages anyone may visit without signing in, in the order search engines should see them: robots.txt allows
 * them and the sitemap lists them. Each one's route file uses publicPage. Today only the sign-in page.
 */
export const PUBLIC_PATHS: readonly string[] = [ROUTES.signIn]

/**
 * The site's origin, e.g. https://spendwise.example: PUBLIC_URL (shared/config/site.ts), else the development address.
 * Canonical URLs, the sitemap and link previews are built on it.
 */
export function siteUrl(): URL {
  return new URL(process.env[PUBLIC_URL_SETTING] || DEFAULT_PUBLIC_URL)
}

/**
 * The metadata every page starts from (the root layout's): the site's address, the title (a page's own title
 * becomes "<title> | SpendWise"), the description, the icon and the link preview.
 */
export function siteMetadata(): Metadata {
  return {
    metadataBase: siteUrl(),
    title: { default: APP_NAME, template: `%s | ${APP_NAME}` },
    description: APP_DESCRIPTION,
    applicationName: APP_NAME,
    icons: { icon: "/favicon.svg" },
    openGraph: { type: "website", siteName: APP_NAME, title: APP_NAME, description: APP_DESCRIPTION },
  }
}

/** A public page's metadata: indexed, under its own title and canonical address. */
export function publicPage(title: string, path: string): Metadata {
  return { title, alternates: { canonical: path }, openGraph: { title, url: path } }
}

/**
 * A signed-in page's metadata: its title for the browser tab, and kept out of search engines. A crawler never signs
 * in, so all it would ever find there is a redirect to the sign-in page.
 */
export function privatePage(title: string): Metadata {
  return { title, robots: { index: false, follow: false } }
}
