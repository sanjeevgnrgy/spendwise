"""HTTP routes for receipts: they only translate HTTP into the use cases and queries.

The receipts module's REST adapter. module.create_router builds the router with the use cases passed in (an uploader
and an extractor), and the composition root mounts it under /api/v1.
"""

from fastapi import APIRouter, Request, Response, UploadFile

from app.modules.receipts.application.extract_receipt import ReceiptExtraction, ReceiptExtractor
from app.modules.receipts.application.upload_receipt import ReceiptUploader
from app.modules.receipts.models import ReceiptRead
from app.modules.receipts.queries.get_receipt import GetReceipt
from app.modules.receipts.values import MAX_RECEIPT_BYTES
from app.web.dependencies import BusDep, ClockDep, IdPath

TAG = "receipts"


def create_router(uploader: ReceiptUploader, extractor: ReceiptExtractor) -> APIRouter:
    """The routes, with the use cases handed in (constructor injection) rather than found globally.

    Plain `def` routes: reading and writing the file and calling the model block, so FastAPI runs them in a worker
    thread and other requests aren't held up.
    """
    router = APIRouter(tags=[TAG])

    # POST /api/v1/receipts: one receipt, as multipart/form-data with the file in the "file" field. 201 with the
    # receipt and its Location. The type is read from the file's bytes; an empty, too large or unsupported file is a
    # 422 (business-rule). FastAPI has already spooled the upload to a temporary file; at most one byte past the
    # limit is read from it, enough to know it's too large.
    @router.post("/receipts", status_code=201)
    def upload_receipt(file: UploadFile, bus: BusDep, request: Request, response: Response) -> ReceiptRead:
        receipt_id = uploader.upload(file.file.read(MAX_RECEIPT_BYTES + 1))
        # 201 Created says where the new resource lives (url_for includes the /api/v1 prefix).
        response.headers["Location"] = str(request.url_for(get_receipt.__name__, receipt_id=receipt_id))
        return bus.ask(GetReceipt(receipt_id=receipt_id)).public()

    # GET /api/v1/receipts/{receipt_id}: what's known about an uploaded receipt (not its bytes). 404 if unknown.
    @router.get("/receipts/{receipt_id}")
    def get_receipt(receipt_id: IdPath, bus: BusDep) -> ReceiptRead:
        return bus.ask(GetReceipt(receipt_id=receipt_id)).public()

    # POST /api/v1/receipts/{receipt_id}/extraction: read the receipt with the model and answer what it says, as a
    # suggestion (nothing is saved). POST, not GET: each call asks the model again, which takes seconds and quota.
    # 404 for an unknown receipt or a missing file; 502 if the model fails or can't be understood.
    @router.post("/receipts/{receipt_id}/extraction")
    def extract_receipt(receipt_id: IdPath, clock: ClockDep) -> ReceiptExtraction:
        return extractor.extract(receipt_id, clock.today())

    return router
