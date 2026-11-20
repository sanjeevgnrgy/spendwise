"""A receipt's file, for its owner only: ReceiptFiles.content(owner_id, receipt_id).

A use case (application layer) of the receipts module, and its public way to hand a receipt's bytes to another
module: the assistant sends them to the receipt agent (Phase 24). Not a handler: it reads the FileStore, which a
handler's database session shouldn't wait on. The owner is checked first, in the same query that finds the receipt
(D190), so nobody's file is read for anyone else.
"""

import logging
from dataclasses import dataclass

from app.core.cqrs import MessageBus
from app.core.errors import NotFoundError
from app.core.files import FileStore
from app.core.i18n import translatable
from app.modules.receipts.i18n import ReceiptText
from app.modules.receipts.models import ReceiptContent
from app.modules.receipts.queries.get_receipt import GetReceipt

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReceiptFiles:
    """Reads uploaded receipts' bytes. Needs the bus (the receipt's row) and the FileStore (its bytes)."""

    bus: MessageBus
    files: FileStore

    def content(self, owner_id: int, receipt_id: int) -> ReceiptContent:
        """One of `owner_id`'s receipts: its bytes and the media type read from them at upload.

        Raises NotFoundError (404) for a receipt they don't have (unknown, or another person's: the same answer,
        D190), or one whose file is gone (the uploads folder was moved or emptied).
        """
        stored = self.bus.ask(GetReceipt(owner_id=owner_id, receipt_id=receipt_id))
        try:
            data = self.files.read(stored.storage_key)
        except FileNotFoundError as exc:
            logger.warning("receipt %s: no file under key %s", stored.id, stored.storage_key)
            raise NotFoundError(translatable(ReceiptText.FILE_MISSING, receipt_id=stored.id)) from exc
        return ReceiptContent(data=data, media_type=stored.media_type)
