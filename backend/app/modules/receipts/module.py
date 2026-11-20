"""How the composition root plugs this module in: its handlers, routes and tables. Nothing else uses it.

The receipts module's wiring. bootstrap.py calls register_handlers() when it builds the bus, builds ReceiptFiles
with create_files() (for the assistant, which sends a receipt's bytes to the receipt agent), mounts the router from
create_router(), and gives TABLES to the migrations. Other modules use the contract in __init__.py instead.
"""

from fastapi import APIRouter

from app.core.cqrs import MessageBus
from app.core.files import FileStore
from app.modules.receipts import api
from app.modules.receipts.application.receipt_files import ReceiptFiles
from app.modules.receipts.application.upload_receipt import ReceiptUploader
from app.modules.receipts.commands.store_receipt import StoreReceipt, store_receipt
from app.modules.receipts.persistence.tables import TABLES
from app.modules.receipts.queries.get_receipt import GetReceipt, get_receipt


def register_handlers(bus: MessageBus) -> None:
    """Tell the bus which function handles each of this module's commands and queries."""
    bus.register(StoreReceipt, store_receipt)
    bus.register(GetReceipt, get_receipt)


def create_files(bus: MessageBus, files: FileStore) -> ReceiptFiles:
    """ReceiptFiles, which hands an owner's receipt to another module (the assistant)."""
    return ReceiptFiles(bus=bus, files=files)


def create_router(bus: MessageBus, files: FileStore) -> APIRouter:
    """The receipts routes, around the upload use case (built here)."""
    return api.create_router(ReceiptUploader(bus=bus, files=files))


__all__ = ["TABLES", "create_files", "create_router", "register_handlers"]
