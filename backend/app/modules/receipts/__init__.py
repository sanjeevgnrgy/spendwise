"""Receipts module: uploaded receipt files (photos and PDFs), kept for their owner.

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.receipts`. The table, the handlers, the upload and the router stay private to this module; the
composition root (bootstrap.py) plugs those in through module.py.

Inside: commands/ and queries/ hold one message and its handler each (StoreReceipt, GetReceipt); application/ holds
the two use cases that aren't bus messages (uploading, which writes a file, and ReceiptFiles, which reads one);
domain/file_types.py is the rule for what may be uploaded; values.py, models.py and i18n/ hold what they share; the
table is in persistence/. The files' bytes are kept in the FileStore (core/files.py), never in the database.
A receipt belongs to the person who uploaded it: every lookup names its owner, and nobody else can see it, have it
read, or attach it (D190).

Who uses it: the assistant takes an attached receipt's bytes from ReceiptFiles and sends them to the receipt agent
(Phase 24), which reads them; the export script takes the limits for the web contract. The module depends on no
other module.
"""

from app.modules.receipts.application.receipt_files import ReceiptFiles
from app.modules.receipts.i18n import ReceiptText
from app.modules.receipts.models import ReceiptContent, ReceiptRead
from app.modules.receipts.values import MAX_RECEIPT_BYTES, ReceiptId, ReceiptMediaType

__all__ = [
    "MAX_RECEIPT_BYTES",
    "ReceiptContent",
    "ReceiptFiles",
    "ReceiptId",
    "ReceiptMediaType",
    "ReceiptRead",
    "ReceiptText",
]
