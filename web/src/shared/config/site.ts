// The setting that says where people open the app, and its development default: canonical URLs, the sitemap, link
// previews (app/_seo/seo.ts) and whether the pages are served over HTTPS (security-headers.ts, for HSTS) come from it.
// Part of shared/config. No imports on purpose: next.config.ts reads it too, before any path alias exists.

/** The web server's setting (web/.env, or the environment): the same value as the backend's PUBLIC_URL. */
export const PUBLIC_URL_SETTING = "PUBLIC_URL"

/** The development address (npm run dev), used when PUBLIC_URL isn't set. */
export const DEFAULT_PUBLIC_URL = "http://localhost:5173"
