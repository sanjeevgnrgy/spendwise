// The insights catalog's downloadReport function (D209): a report card's Download CSV and Download report (.md)
// buttons. Part of the assistant feature's A2UI renderer, listed in client-functions.ts. The card gives only a month
// and a format, both checked here; the browser builds the address itself and fetches the file as the signed-in
// person (the session cookie, X-CSRF and the language from `api`), so a card can't point the browser anywhere else.

import { MONTH_PATTERN, REPORT_FORMATS } from "@/shared/api/contracts.gen"
import { api, unwrapFile, type Schemas } from "@/shared/api/http"
import { isObject } from "@/shared/lib/guards"
import { saveFile } from "@/shared/lib/save-file"

type ReportFormat = Schemas["ReportFormat"]

const MONTH = new RegExp(MONTH_PATTERN)

/** Whether a value is one of the report's download formats ("csv", "md"). */
function isReportFormat(value: unknown): value is ReportFormat {
  return REPORT_FORMATS.some((format) => format === value)
}

/**
 * Checks downloadReport's arguments ({month: "2026-11", format: "csv"}). Gives what a click runs: fetch that month's
 * file in that format and save it under the name the server gave it. Null if the arguments aren't valid.
 */
export function downloadReport(args: unknown): (() => Promise<void>) | null {
  if (!isObject(args) || typeof args.month !== "string" || !MONTH.test(args.month)) return null
  const { month, format } = args
  if (!isReportFormat(format)) return null
  return async () => {
    const request = { params: { path: { month, format } }, parseAs: "blob" } as const
    const file = await unwrapFile(api.GET("/api/v1/reports/monthly/{month}/{format}", request))
    saveFile(file.blob, file.name ?? `${month}.${format}`)
  }
}
