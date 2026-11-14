"""The receipts module's read models: ReceiptRead (what anyone may see of an uploaded receipt) and StoredReceipt (the
same, plus where its bytes are kept, for this module only).

Part of the module's contract layer. The GetReceipt query (queries/) returns a StoredReceipt; api.py sends its public
part from the upload and GET routes; the extraction (application/extract_receipt.py) reads the file by its key.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# What the API says about an uploaded receipt (POST /receipts, GET /receipts/{id}). A Pydantic model, so its
# docstring below is part of the API schema: explanations go in these comments instead.
class ReceiptRead(BaseModel):
    """An uploaded receipt file."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    # The type read from the file's bytes (values.ReceiptMediaType), e.g. "image/jpeg".
    media_type: str
    size_bytes: int
    # When it was uploaded (UTC).
    created_at: datetime


# A receipt as the module itself needs it: with the key its bytes are stored under (core/files.FileStore). The key
# is an internal detail, so it never leaves the module (public() drops it).
class StoredReceipt(ReceiptRead):
    storage_key: str

    def public(self) -> ReceiptRead:
        """The part anyone may see: everything but the storage key."""
        return ReceiptRead.model_validate(self.model_dump(exclude={"storage_key"}))
