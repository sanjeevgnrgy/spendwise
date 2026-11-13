// The one way to turn anything thrown into a message for people.
export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

// A request we cancelled ourselves (the page was left, or Stop was pressed): not an error to show.
export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}
