"""GetReceipt: one uploaded receipt by id. The query and its handler; it never changes anything.

A slice of the receipts module's read side. module.py registers the handler with the bus. The routes ask it (the
upload's answer, GET /receipts/{id}) and so does the extraction, which needs the storage key. The answer is a frozen
StoredReceipt copy (models.py), never a table row.
"""

from app.core.cqrs import Context, Query
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.modules.receipts.i18n import ReceiptText
from app.modules.receipts.models import StoredReceipt
from app.modules.receipts.persistence.tables import ReceiptFile
from app.modules.receipts.values import ReceiptId


# One receipt: its row, with the storage key (only this module reads that: StoredReceipt.public() drops it).
class GetReceipt(Query[StoredReceipt]):
    """One uploaded receipt. Raises NotFoundError if there's no such receipt."""

    receipt_id: ReceiptId


def get_receipt(ctx: Context, query: GetReceipt) -> StoredReceipt:
    """One receipt by id. Raises NotFoundError (catalogued text) if there's no such receipt."""
    row = ctx.session.get(ReceiptFile, query.receipt_id)
    if row is None:
        raise NotFoundError(translatable(ReceiptText.NOT_FOUND, receipt_id=query.receipt_id))
    return StoredReceipt.model_validate(row)
