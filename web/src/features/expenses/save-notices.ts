// What the server noticed about a save (a budget pushed near or over its limit, D212), shown to the person. Part of
// the expenses feature; used by the Add dialog and the table's inline editing after a successful save.

import { toast } from "sonner"

/**
 * Shows each notice as a warning toast. The notices are texts the server wrote for people, in the language of the
 * request, so they're shown as they are (D178: server texts aren't translated in the browser).
 */
export function showSaveNotices(notices: readonly string[]): void {
  for (const notice of notices) toast.warning(notice)
}
