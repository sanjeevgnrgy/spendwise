// The web app's Next.js setup: the rewrite that puts the API on the web app's own origin, the proxy settings it needs,
// and the pages' security headers. Read by `next dev`, `next build` and `next start`. It imports the generated contract
// (no imports of its own), so the proxied prefix can't disagree with the app's API calls.

import type { NextConfig } from "next"

import { PAGES_SOURCE, securityHeaders } from "./security-headers"
import { API_PREFIX } from "./src/shared/api/contracts.gen"

// The server's setting (web/.env, or the environment) for where the backend runs. It has no NEXT_PUBLIC_ prefix on
// purpose: only this file reads it, in Node, and it never reaches the browser's code.
const API_PROXY_TARGET = "API_PROXY_TARGET"
// Where .\run.ps1 starts the backend. 127.0.0.1, not localhost: Node may resolve localhost to ::1 (IPv6), where
// uvicorn isn't listening.
const DEFAULT_API_TARGET = "http://127.0.0.1:8000"
// How long a proxied call may go without a byte before Next gives up (its default is 30 s). /parse and reading a
// receipt wait on Gemini for up to two attempts of 60 s with nothing sent meanwhile; the assistant's stream pings
// every 15 s, so it never comes close.
const PROXY_TIMEOUT_MS = 180_000

const target = process.env[API_PROXY_TARGET] || DEFAULT_API_TARGET

/**
 * Next.js's configuration (https://nextjs.org/docs/app/api-reference/config/next-config-js).
 * - The browser calls /api/v1/... on the web app's origin, and Next forwards it to the backend (D184, D188). The
 *   rewrite runs before the app's own routes ("beforeFiles"), so no page route can claim it.
 * - Every page gets the security headers (security-headers.ts, D193); the API's responses carry the backend's.
 * - No compression: Next would gzip the assistant's Server-Sent Events too, and hold them back until a buffer fills.
 *   In production the reverse proxy in front compresses (and is set not to buffer the stream).
 * - No "X-Powered-By" header: it only tells others what the server runs.
 * - No generated web/AGENTS.md: `next dev` would write one for AI agents. The repository's rules live in one file, the
 *   root AGENTS.md, which points agents to the Next.js docs bundled in node_modules/next/dist/docs instead.
 */
const config: NextConfig = {
  compress: false,
  poweredByHeader: false,
  agentRules: false,
  async headers() {
    return [{ source: PAGES_SOURCE, headers: securityHeaders() }]
  },
  async rewrites() {
    return {
      beforeFiles: [{ source: `${API_PREFIX}/:path*`, destination: `${target}${API_PREFIX}/:path*` }],
      afterFiles: [],
      fallback: [],
    }
  },
  experimental: { proxyTimeout: PROXY_TIMEOUT_MS },
}

export default config
