// Shared helpers for errors: the kind of error whose message is written for people, one way to turn anything thrown
// into a message to show, logging what people aren't shown, and a check for a request that was cancelled on purpose.
// Part of shared/lib. Used by the pages, dialogs, toasts and error boundaries (messageOf), the query cache and the
// assistant (reportUnexpected), and the HTTP client and the assistant (UserFacingError, isAbort).

import { i18n } from "@/shared/i18n"

/**
 * An error whose message was written for people: a server's problem detail or run error (the server only sends
 * texts for people, D180), or one of the app's own texts. Only these are shown as they are.
 */
export class UserFacingError extends Error {}

/**
 * The message to show for anything thrown. A UserFacingError's own message; for anything else (a bug, a library's
 * error, like "Cannot read properties of undefined") a generic text in the language on now, because such messages are
 * for developers and can carry internals. The details stay in the browser console (the error boundaries log them).
 */
export function messageOf(error: unknown): string {
  return error instanceof UserFacingError ? error.message : i18n.t("errors.unexpected")
}

/**
 * Logs an error people are only shown a generic text for (anything but a UserFacingError or a cancellation) to the
 * browser console, so developers still see what happened. Used by the query cache and the assistant's runs; the error
 * boundaries log what they catch themselves.
 */
export function reportUnexpected(error: unknown): void {
  if (!isAbort(error) && !(error instanceof UserFacingError)) console.error(error)
}

/** Whether this is a request we cancelled ourselves (the page was left, or Stop was pressed): not an error to show. */
export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}
