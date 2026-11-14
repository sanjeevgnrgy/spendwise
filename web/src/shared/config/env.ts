// The settings this build reads from its environment (web/.env, see .env.example). Part of shared/config. Used by
// the shared HTTP client and the assistant's stream, which both talk to the backend.

/** Where the backend runs: VITE_API_URL if it's set (in web/.env, when the backend moves), else localhost:8000. */
export const API_ORIGIN: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
