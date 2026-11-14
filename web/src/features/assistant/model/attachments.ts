// What may be attached in the chat: a receipt, as a photo or a PDF, within the server's size limit. Pure functions
// over the contract's values, so the browser refuses at once what the server would refuse after the upload. Part of
// the assistant feature (model/). Used by the composer's attach button (components/attach-button.tsx).

import { LIMITS, RECEIPT_MEDIA_TYPES } from "@/shared/api/contracts.gen"

/** Why a file can't be attached, as a key of the composer's texts; the server still checks the file's bytes. */
export type AttachmentProblem = "attachmentTooLarge" | "attachmentType"

const BYTES_PER_MB = 1024 * 1024
/** The largest receipt, in MB, as the texts say it (LIMITS.receiptBytes is the rule). */
export const MAX_RECEIPT_MB = LIMITS.receiptBytes / BYTES_PER_MB

/** What the file picker offers: the receipt types, as its `accept` attribute wants them. */
export const RECEIPT_ACCEPT = RECEIPT_MEDIA_TYPES.join(",")

/** Whether a type the browser reports is one a receipt may be (it narrows the string to that union). */
function isReceiptType(type: string): type is (typeof RECEIPT_MEDIA_TYPES)[number] {
  return RECEIPT_MEDIA_TYPES.some((allowed) => allowed === type)
}

/**
 * Why this file can't be attached, or undefined if it can. The type is the one the browser reports (from the file's
 * name): a first check only, since the server reads the file's own bytes.
 */
export function attachmentProblem(file: File): AttachmentProblem | undefined {
  if (file.size > LIMITS.receiptBytes) return "attachmentTooLarge"
  if (!isReceiptType(file.type)) return "attachmentType"
  return undefined
}
