// What a change touched. A mutation says which kind of data it changed (its `meta.changes`), and the app
// decides, in one place (app/_shell/query-client.ts), which cached data that makes out of date. Features don't
// need to know which other features show the same data. Part of shared/config. Used by the features' mutations,
// app/_shell/query-client.ts (STALE_AFTER) and app/_shell/providers.tsx (the assistant's changes).

/**
 * The kinds of data a change can touch. Adding one here makes app/_shell/query-client.ts fail to compile until it says
 * what that kind of change makes out of date.
 */
export const DATA_SCOPES = {
  expenses: "expenses",
  // The signed-in person's own account (the Settings page): where they're signed in, and their access tokens.
  sessions: "sessions",
  accessTokens: "accessTokens",
} as const

/** One of DATA_SCOPES' values: what a mutation's `meta.changes` holds. */
export type DataScope = (typeof DATA_SCOPES)[keyof typeof DATA_SCOPES]

// Teach TanStack Query the shape of a mutation's `meta`, so `meta.changes` is checked by TypeScript.
declare module "@tanstack/react-query" {
  interface Register {
    mutationMeta: { changes?: DataScope }
  }
}
