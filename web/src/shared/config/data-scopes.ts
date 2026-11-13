// What a change touched. A mutation says which kind of data it changed (its `meta.changes`), and the app
// decides, in one place (app/query-client.ts), which cached data that makes out of date. Features don't
// need to know which other features show the same data.
export const DATA_SCOPES = {
  expenses: "expenses",
} as const

export type DataScope = (typeof DATA_SCOPES)[keyof typeof DATA_SCOPES]

// Teach TanStack Query the shape of a mutation's `meta`, so `meta.changes` is checked by TypeScript.
declare module "@tanstack/react-query" {
  interface Register {
    mutationMeta: { changes?: DataScope }
  }
}
