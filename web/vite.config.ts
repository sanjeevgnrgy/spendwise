// The web app's build and dev-server setup (Vite): its plugins, the "@/..." import alias, and the proxy that puts the
// API on the web app's own origin. Read by `npm run dev`, `npm run build` and `npm run preview`. It imports three
// files from src/ that have no imports of their own (the app's name, the theme's boot script and the generated
// contract), so index.html and the proxy can't disagree with the app.

import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin, type ProxyOptions } from 'vite'

import { API_PREFIX } from './src/shared/api/contracts.gen.ts'
import { APP_NAME } from './src/shared/config/app.ts'
import { THEME_BOOT_SCRIPT } from './src/shared/theme/theme-constants.ts'

// What index.html writes where the app's name goes (in its <title>).
const APP_NAME_PLACEHOLDER = '%APP_NAME%'

// The dev server's setting (web/.env) for where the backend runs. It has no VITE_ prefix on purpose: it's read here,
// in Node, and never reaches the browser's code.
const API_PROXY_TARGET = 'API_PROXY_TARGET'
// Where .\run.ps1 starts the backend. 127.0.0.1, not localhost: Node may resolve localhost to ::1 (IPv6), where
// uvicorn isn't listening.
const DEFAULT_API_TARGET = 'http://127.0.0.1:8000'

// index.html can't import the app's code, so this fills it in at build time: the app's name, and the
// script that applies the saved theme before the first paint. Each is written once, in src/.
function fromAppSource(): Plugin {
  return {
    name: 'spendwise-index-html',
    transformIndexHtml: (html) => ({
      html: html.replaceAll(APP_NAME_PLACEHOLDER, APP_NAME),
      tags: [{ tag: 'script', children: THEME_BOOT_SCRIPT, injectTo: 'head-prepend' }],
    }),
  }
}

/**
 * The proxy rule that serves the API on the web app's origin (D184): the browser calls /api/v1/... on the page's own
 * address, and the dev server forwards it to `target`. One origin means no CORS, and (Phase 22) a session cookie the
 * browser only sends to this app. In production a reverse proxy does the same job.
 */
function apiProxy(target: string): Record<string, ProxyOptions> {
  // changeOrigin stays false: the backend sees the browser's Host, so the URLs it builds (the Location of a new
  // expense or receipt) point at the web app's address, as they will behind a production proxy.
  return { [API_PREFIX]: { target, changeOrigin: false } }
}

/**
 * Vite's configuration (https://vite.dev/config/): React, Tailwind 4, the index.html filler above, the "@" alias for
 * src/, and the API proxy for `npm run dev` (`npm run preview` uses the same one).
 */
export default defineConfig(({ mode }) => {
  // '' loads every variable in web/.env, not only VITE_ ones; a real environment variable wins over the file.
  const env = loadEnv(mode, import.meta.dirname, '')
  return {
    plugins: [react(), tailwindcss(), fromAppSource()],
    resolve: {
      // "@/shared/ui/button" means "src/shared/ui/button", from any file, at any depth.
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: { proxy: apiProxy(env[API_PROXY_TARGET] || DEFAULT_API_TARGET) },
  }
})
