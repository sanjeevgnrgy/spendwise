// Saving a file the app fetched (a report download) through the browser's own download, without a page change.
// Part of shared/lib (it knows no feature). Used by the assistant's report card (its downloadReport function).

// How long the file's temporary address stays valid after the download starts: long enough for the browser to have
// read it, short enough not to keep the bytes in memory.
const REVOKE_AFTER_MS = 10_000

/**
 * Saves `blob` as a file called `name`, as a link with a `download` attribute would. The temporary object URL is
 * revoked shortly after, so the bytes don't stay in memory.
 */
export function saveFile(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = name
  link.rel = "noopener"
  document.body.append(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS)
}
