"""The receipts module's shared values: its id type, limits and the kinds of file it accepts.

Part of the module's contract layer. The upload check (domain/file_types.py), the command (commands/) and the table
(persistence/tables.py) use them; __init__.py exports what
other modules and the web contract need. This file imports no other file of the module.
"""

from enum import StrEnum

from app.core.ids import RecordId

ReceiptId = RecordId

# The largest file accepted: 5 MB. Enough for a phone photo or a scanned page; anything bigger is refused before
# it's stored or sent to the model.
BYTES_PER_MB = 1024 * 1024
MAX_RECEIPT_MB = 5
MAX_RECEIPT_BYTES = MAX_RECEIPT_MB * BYTES_PER_MB


# The kinds of file a receipt may be: the photos a phone takes or a browser offers, and PDFs. The type is read
# from the file's first bytes (domain/file_types.py), never taken from the name or the header the client sent.
class ReceiptMediaType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"
    PDF = "application/pdf"


# Column sizes (persistence/tables.py). A storage key is a UUID's 32 hex digits (infrastructure/files.py);
# a media type is one of ReceiptMediaType's values.
STORAGE_KEY_LENGTH = 32
MAX_MEDIA_TYPE_LENGTH = max(len(media_type) for media_type in ReceiptMediaType)
