// Shared checks for data from the network, which TypeScript can't vouch for: they narrow `unknown` safely instead
// of casting it with `as`. Part of shared/lib. Used by the HTTP client (problem bodies), format.ts, and the
// assistant (stream events, A2UI messages).

/** Whether a value is a plain object (not null, not an array), so its properties can be read and checked. */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

/**
 * Looks a server value up in a fixed table (class names, icons...); anything else gives undefined. Server values
 * are only ever used as keys like this, never pasted into class names or styles. Only the table's own keys
 * count, so "toString" or "__proto__" can't reach anything inherited.
 */
export function pick<T>(table: Record<string, T>, value: unknown): T | undefined {
  return typeof value === "string" && Object.hasOwn(table, value) ? table[value] : undefined
}
