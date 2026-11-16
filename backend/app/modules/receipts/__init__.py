"""Receipts module: uploaded receipt files (photos and PDFs), and reading one into an expense suggestion.

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.receipts`. The table, the handlers, the upload and the router stay private to this module; the
composition root (bootstrap.py) plugs those in through module.py.

Inside: commands/ and queries/ hold one message and its handler each (StoreReceipt, GetReceipt); application/ holds
the two use cases that aren't bus messages (uploading, which writes a file, and reading a receipt with the model);
domain/file_types.py is the rule for what may be uploaded; values.py, models.py and i18n/ hold what they share; the
table is in persistence/. The files' bytes are kept in the FileStore (core/files.py), never in the database.
A receipt belongs to the person who uploaded it: every lookup names its owner, and nobody else can see it, have it
read, or attach it (D190).

Who uses it: the assistant reads an attached receipt with ReceiptExtractor to pre-fill the expense form. The
module itself asks categories (the names a suggestion may use) and uses expenses' PaymentMethod.
"""

from app.modules.receipts.application.extract_receipt import LineItem, ReceiptExtraction, ReceiptExtractor
from app.modules.receipts.i18n import ReceiptText
from app.modules.receipts.models import ReceiptRead
from app.modules.receipts.values import MAX_RECEIPT_BYTES, ReceiptId, ReceiptMediaType

__all__ = [
    "MAX_RECEIPT_BYTES",
    "LineItem",
    "ReceiptExtraction",
    "ReceiptExtractor",
    "ReceiptId",
    "ReceiptMediaType",
    "ReceiptRead",
    "ReceiptText",
]
