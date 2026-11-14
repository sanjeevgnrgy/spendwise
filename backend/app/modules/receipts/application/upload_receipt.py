"""Uploading a receipt: check the file, keep its bytes, record it. The use case behind POST /receipts.

A use case (application layer) of the receipts module, built by module.py and called by api.py. The file is checked
(domain/file_types.py) before anything is stored, saved in the FileStore under a random key, and then recorded with
StoreReceipt. If recording fails, the file is deleted again, so no file is ever kept without its row.
"""

from dataclasses import dataclass

from app.core.cqrs import MessageBus
from app.core.files import FileStore
from app.modules.receipts.commands.store_receipt import StoreReceipt
from app.modules.receipts.domain.file_types import check_receipt_file


@dataclass(frozen=True)
class ReceiptUploader:
    """Keeps uploaded receipts. Needs the bus (to record them) and the FileStore (for their bytes)."""

    bus: MessageBus
    files: FileStore

    def upload(self, data: bytes) -> int:
        """Keep the file and return the new receipt's id.

        Raises BusinessRuleError (422) if the file is empty, over MAX_RECEIPT_BYTES or not a JPEG, PNG, WEBP or PDF.
        """
        media_type = check_receipt_file(data)
        key = self.files.save(data)
        try:
            return self.bus.execute(StoreReceipt(storage_key=key, media_type=media_type, size_bytes=len(data)))
        except BaseException:
            # Without its row the file could never be found again: don't keep it.
            self.files.delete(key)
            raise
