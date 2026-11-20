"""HTTP routes for receipts: they only translate HTTP into the use cases and queries.

The receipts module's REST adapter. module.create_router builds the router with the upload use case passed in, and
the composition root mounts it under /api/v1. Reading a receipt isn't a route: the assistant sends it to the receipt
agent (Phase 24, D199).
"""

from fastapi import APIRouter, Request, Response, UploadFile

from app.modules.receipts.application.upload_receipt import ReceiptUploader
from app.modules.receipts.models import ReceiptRead
from app.modules.receipts.queries.get_receipt import GetReceipt
from app.modules.receipts.values import MAX_RECEIPT_BYTES
from app.web.auth import CurrentUserDep
from app.web.dependencies import BusDep, IdPath

TAG = "receipts"


def create_router(uploader: ReceiptUploader) -> APIRouter:
    """The routes, with the upload use case handed in (constructor injection) rather than found globally.

    Plain `def` routes: reading and writing the file block, so FastAPI runs them in a worker thread and other requests
    aren't held up.
    """
    router = APIRouter(tags=[TAG])

    # POST /api/v1/receipts: one receipt, as multipart/form-data with the file in the "file" field. 201 with the
    # receipt and its Location. The type is read from the file's bytes; an empty, too large or unsupported file is a
    # 422 (business-rule). FastAPI has already spooled the upload to a temporary file; at most one byte past the
    # limit is read from it, enough to know it's too large.
    @router.post("/receipts", status_code=201)
    def upload_receipt(
        file: UploadFile, principal: CurrentUserDep, bus: BusDep, request: Request, response: Response
    ) -> ReceiptRead:
        owner = principal.user_id
        receipt_id = uploader.upload(owner, file.file.read(MAX_RECEIPT_BYTES + 1))
        # 201 Created says where the new resource lives (url_for includes the /api/v1 prefix).
        response.headers["Location"] = str(request.url_for(get_receipt.__name__, receipt_id=receipt_id))
        return bus.ask(GetReceipt(owner_id=owner, receipt_id=receipt_id)).public()

    # GET /api/v1/receipts/{receipt_id}: what's known about one of the signed-in person's receipts (not its bytes).
    # 404 if they have no such receipt (another person's is never shown, D190).
    @router.get("/receipts/{receipt_id}")
    def get_receipt(receipt_id: IdPath, principal: CurrentUserDep, bus: BusDep) -> ReceiptRead:
        return bus.ask(GetReceipt(owner_id=principal.user_id, receipt_id=receipt_id)).public()

    return router
