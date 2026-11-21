"""The receipts module's table: `receipt_file`, one row per uploaded receipt.

Private to this module: only its own handlers (the slices in commands/ and queries/) read or write it. Other modules
ask through the contract (the package's __init__.py), and the composition root hands TABLES to the migrations. The
table itself is created and changed by Alembic migrations, never by the app.
"""

from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.modules.receipts.values import MAX_MEDIA_TYPE_LENGTH, STORAGE_KEY_LENGTH


# A SQLModel table class: its docstring stays as it is; notes go in comments.
class ReceiptFile(SQLModel, table=True):
    """An uploaded receipt. Private to the receipts module: other modules never import it."""

    __tablename__ = "receipt_file"  # pyright: ignore[reportAssignmentType]  (SQLModel declares it as declared_attr)

    # None until the row is inserted; the database assigns it (see the flush in commands/store_receipt.py).
    id: int | None = Field(default=None, primary_key=True)
    # Who uploaded it (core.ids.UserId; no foreign key: the users table is the accounts module's). Only they can see
    # it, read it with the model or attach it in the chat (D190).
    owner_id: int = Field(index=True)
    # Where the bytes are kept: a random key the FileStore made, never a name the user sent. Unique: one file, one row.
    storage_key: str = Field(max_length=STORAGE_KEY_LENGTH, unique=True)
    # The type read from the file's first bytes (values.ReceiptMediaType), so the model is told the truth about it.
    media_type: str = Field(max_length=MAX_MEDIA_TYPE_LENGTH)
    size_bytes: int
    # When it was uploaded: UTC, from the app's clock (store_receipt), stored with its time zone.
    created_at: datetime = Field(sa_type=DateTime(timezone=True))


# Every table this module owns, for the composition root (bootstrap.metadata(), used by the migrations).
TABLES = (ReceiptFile,)
