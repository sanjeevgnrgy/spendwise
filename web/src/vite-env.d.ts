/// <reference types="vite/client" />

// The environment variables this app reads (from web/.env), so they're typed instead of `any`.
interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
