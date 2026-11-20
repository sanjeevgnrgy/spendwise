"""The receipts module's texts for people, in English: their keys, and the source every other language translates.

Part of the receipts module (i18n/). Only what a person reads: the errors of an upload and of finding a receipt (a
problem's detail). Reading a receipt is the receipt agent's (Phase 24), and its errors are the assistant's texts.
hi.py translates these; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class ReceiptText(StrEnum):
    """The receipts module's texts, by key."""

    EMPTY_FILE = "errors.emptyFile"
    TOO_LARGE = "errors.tooLarge"
    UNSUPPORTED_TYPE = "errors.unsupportedType"
    NOT_FOUND = "errors.notFound"
    FILE_MISSING = "errors.fileMissing"


EN: dict[ReceiptText, TextValue] = {
    ReceiptText.EMPTY_FILE: "The file is empty.",
    # {max_mb} is MAX_RECEIPT_BYTES in megabytes.
    ReceiptText.TOO_LARGE: "The file is larger than {max_mb} MB. Try a smaller photo or a shorter PDF.",
    ReceiptText.UNSUPPORTED_TYPE: "Only photos (JPEG, PNG or WEBP) and PDF files can be read as receipts.",
    ReceiptText.NOT_FOUND: "Receipt {receipt_id} not found",
    # The row is there but its file isn't (the uploads folder was moved or emptied); where it was goes to the log.
    ReceiptText.FILE_MISSING: "The file for receipt {receipt_id} is missing. Upload it again.",
}
