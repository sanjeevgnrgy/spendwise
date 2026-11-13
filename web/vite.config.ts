import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

import { APP_NAME } from './src/shared/config/app.ts'
import { THEME_BOOT_SCRIPT } from './src/shared/theme/theme-constants.ts'

const APP_NAME_PLACEHOLDER = '%APP_NAME%'

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

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), fromAppSource()],
  resolve: {
    // "@/shared/ui/button" means "src/shared/ui/button", from any file, at any depth.
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
})
