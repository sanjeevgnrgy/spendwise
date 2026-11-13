// Where the backend runs. Override it with VITE_API_URL in web/.env if it moves.
export const API_ORIGIN: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
