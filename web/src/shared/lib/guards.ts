// Checks for data from the network, which TypeScript can't vouch for.

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

// Look a server value up in a fixed table (class names, icons...); anything else gives undefined.
// Server values are only ever used as keys like this, never pasted into class names or styles.
export function pick<T>(table: Record<string, T>, value: unknown): T | undefined {
  return typeof value === "string" && Object.hasOwn(table, value) ? table[value] : undefined
}
