// The security headers every page is sent with (D193): what the browser may load and run, who may frame the app, and
// what it tells other sites. Build configuration, read by next.config.ts (its headers()), next to it for the same
// reason: it imports only files without path aliases. The API's responses aren't covered here: the backend sends its
// own (backend/app/web/security_headers.py), and Next passes them through.

import { API_PREFIX } from "./src/shared/api/contracts.gen"
import { DEFAULT_PUBLIC_URL, PUBLIC_URL_SETTING } from "./src/shared/config/site"

// `next dev` runs with this NODE_ENV; it needs eval (fast refresh) and a websocket (hot reload).
const DEVELOPMENT = "development"
// Two years: the usual HSTS lifetime for a site that serves HTTPS only.
const HSTS_MAX_AGE_SECONDS = 63_072_000
const HTTPS = "https:"

/** One response header, as Next.js's headers() takes it. */
interface Header {
  key: string
  value: string
}

/**
 * The Content-Security-Policy: only this origin's scripts, styles, fonts and API, and https pictures (the identity
 * provider's profile pictures can be on any host). Inline scripts are allowed: Next.js writes its own bootstrap inline
 * and the theme script runs before React. Nonces would remove that need but make every page render per request, so
 * the trade-off is recorded in D193; the policy still blocks scripts from anywhere else, plugins, framing, <base> and
 * form hijacking.
 */
function contentSecurityPolicy(development: boolean, https: boolean): string {
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${development ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    `connect-src 'self'${development ? " ws:" : ""}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ]
  // Over HTTPS, any stray http:// request is upgraded instead of sent in the clear (on http://localhost it'd break).
  if (https) directives.push("upgrade-insecure-requests")
  return directives.join("; ")
}

/**
 * The headers for every page: the CSP, no framing, no type sniffing, no referrer to other sites, no camera or
 * microphone, a separate browsing context group, and, when PUBLIC_URL is https, HSTS. Fixed when the app is built,
 * like the rewrite (PUBLIC_URL must be set before `next build`).
 */
export function securityHeaders(): Header[] {
  const development = process.env.NODE_ENV === DEVELOPMENT
  const https = new URL(process.env[PUBLIC_URL_SETTING] || DEFAULT_PUBLIC_URL).protocol === HTTPS
  const headers: Header[] = [
    { key: "Content-Security-Policy", value: contentSecurityPolicy(development, https) },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "same-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
    { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  ]
  if (https) headers.push({ key: "Strict-Transport-Security", value: `max-age=${HSTS_MAX_AGE_SECONDS}` })
  return headers
}

/** Which paths get them: every one but the API's (the backend's headers cover those). */
export const PAGES_SOURCE = `/((?!${API_PREFIX.slice(1)}/).*)`
