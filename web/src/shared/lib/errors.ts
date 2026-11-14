// Shared helpers for errors: one way to turn anything thrown into a message for people, and a check for a
// request that was cancelled on purpose. Part of shared/lib. Used by the pages, dialogs and toasts (messageOf),
// and by the HTTP client and the assistant (isAbort).

/** The message to show for anything thrown: an Error's message, or the value as text if it isn't an Error. */
export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

/** Whether this is a request we cancelled ourselves (the page was left, or Stop was pressed): not an error to show. */
export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}
