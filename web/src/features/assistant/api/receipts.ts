// The receipts API, as the assistant uses it: upload one file, then point at it from a run by its id. Part of the
// assistant feature (api/). Used by agent-stream.ts, which uploads an attached receipt as the first step of a run
// and sends the message with receiptPart().

import type { DocumentPart, ImagePart } from "@ag-ui/core"

import { AGUI } from "@/shared/api/contracts.gen"
import { api, unwrap, type Schemas } from "@/shared/api/http"

/** An uploaded receipt, as POST /receipts answers: its id and the type the server read from the file's bytes. */
export type Receipt = Schemas["ReceiptRead"]

// Checked against the API's paths, like every other call (a typo is a compile error).
const RECEIPTS_PATH = "/api/v1/receipts"
// The multipart field the route reads the file from (its `file` parameter).
const FILE_FIELD = "file"
// AG-UI's media parts a receipt travels as (a photo is an image part, any other file, a PDF, a document part), and
// the source that names a file the server already holds.
const IMAGE_PART = "image"
const DOCUMENT_PART = "document"
const FILE_SOURCE = "file"
const IMAGE_TYPE_PREFIX = "image/"

/**
 * Uploads one receipt file and returns the receipt. Throws ApiError if it's refused (a 422 saying why: empty, too
 * large, not a photo or PDF) or the server can't be reached, and an AbortError if `signal` stops it.
 */
export async function uploadReceipt(file: File, signal?: AbortSignal): Promise<Receipt> {
  return unwrap(
    api.POST(RECEIPTS_PATH, {
      // The API's schema types a multipart file field as a string (JSON Schema has no file type), so this body only
      // satisfies the type: bodySerializer sends the File itself, and the browser sets the multipart header.
      body: { file: file.name },
      bodySerializer: () => {
        const form = new FormData()
        form.append(FILE_FIELD, file)
        return form
      },
      signal,
    }),
  )
}

/**
 * An uploaded receipt as a part of a user message: an image or document part whose source is the file handle this
 * app issued ({type: "file", value: <id>, provider}). The server reads the file it holds; no bytes travel here.
 */
export function receiptPart(receipt: Receipt): ImagePart | DocumentPart {
  const source = {
    type: FILE_SOURCE,
    value: String(receipt.id),
    provider: AGUI.receiptProvider,
    mimeType: receipt.media_type,
  } as const
  return receipt.media_type.startsWith(IMAGE_TYPE_PREFIX)
    ? { type: IMAGE_PART, source }
    : { type: DOCUMENT_PART, source }
}
