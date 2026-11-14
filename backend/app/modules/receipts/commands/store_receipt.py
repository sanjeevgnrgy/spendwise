"""StoreReceipt: record an uploaded receipt whose bytes are already in the FileStore. The command and its handler.

A slice of the receipts module's write side. module.py registers the handler with the bus; the upload use case
(application/upload_receipt.py) sends it after saving the file, and deletes the file again if this fails. The bus
commits; the handler never does.
"""

from pydantic import Field

from app.core.cqrs import Command, Context
from app.modules.receipts.persistence.tables import ReceiptFile
from app.modules.receipts.values import MAX_RECEIPT_BYTES, STORAGE_KEY_LENGTH, ReceiptMediaType


# Sent by ReceiptUploader only: the file has been checked (domain/file_types.py) and saved; this records it.
class StoreReceipt(Command[int]):
    """Returns the new receipt's id."""

    storage_key: str = Field(min_length=STORAGE_KEY_LENGTH, max_length=STORAGE_KEY_LENGTH)
    media_type: ReceiptMediaType
    size_bytes: int = Field(ge=1, le=MAX_RECEIPT_BYTES)


def store_receipt(ctx: Context, command: StoreReceipt) -> int:
    """Add the receipt's row, stamped with the clock's now (UTC), and return its new id."""
    row = ReceiptFile(
        storage_key=command.storage_key,
        media_type=command.media_type,
        size_bytes=command.size_bytes,
        created_at=ctx.clock.now(),
    )
    ctx.session.add(row)
    # flush sends the INSERT inside the transaction, so the database assigns the id now.
    ctx.session.flush()
    assert row.id is not None
    return row.id
