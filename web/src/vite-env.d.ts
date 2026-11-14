// The types of Vite's import.meta.env for this app (the reference below brings in Vite's own). Read by TypeScript
// only; shared/config/env.ts is the one place that reads these variables.

/// <reference types="vite/client" />

/** The environment variables this app reads (from web/.env), so they're typed instead of `any`. */
interface ImportMetaEnv {
  /** Where the backend runs (see shared/config/env.ts); unset means http://localhost:8000. */
  readonly VITE_API_URL?: string
}

/** Makes import.meta.env use the type above. */
interface ImportMeta {
  readonly env: ImportMetaEnv
}
