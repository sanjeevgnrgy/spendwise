"""GetReceipt: one uploaded receipt by id. The query and its handler; it never changes anything.

A slice of the receipts module's read side. module.py registers the handler with the bus. The routes ask it (the
upload's answer, GET /receipts/{id}) and so does the extraction, which needs the storage key. The answer is a frozen
StoredReceipt copy (models.py), never a table row.
"""

from sqlmodel import select

from app.core.cqrs import Context, Query
from app.core.errors import NotFoundError
from app.core.i18n import translatable
from app.core.ids import UserId
from app.modules.receipts.i18n import ReceiptText
from app.modules.receipts.models import StoredReceipt
from app.modules.receipts.persistence.tables import ReceiptFile
from app.modules.receipts.values import ReceiptId


# One receipt: its row, with the storage key (only this module reads that: StoredReceipt.public() drops it).
class GetReceipt(Query[StoredReceipt]):
    """One of the owner's uploaded receipts. Raises NotFoundError if they have no such receipt."""

    owner_id: UserId
    receipt_id: ReceiptId


def get_receipt(ctx: Context, query: GetReceipt) -> StoredReceipt:
    """One of the owner's receipts by id. Raises NotFoundError (catalogued text) if they have no such receipt.

    The owner and the id are matched in the same statement: another person's receipt is "not found", like one that
    doesn't exist (D190).
    """
    statement = select(ReceiptFile).where(ReceiptFile.id == query.receipt_id, ReceiptFile.owner_id == query.owner_id)
    row = ctx.session.exec(statement).first()
    if row is None:
        raise NotFoundError(translatable(ReceiptText.NOT_FOUND, receipt_id=query.receipt_id))
    return StoredReceipt.model_validate(row)
