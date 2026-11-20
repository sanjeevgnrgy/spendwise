"""The receipts module's use cases that aren't bus messages (application/): uploading a receipt (saving its bytes,
then recording it) and handing its owner's file to another module (ReceiptFiles). Neither is a handler: both use the
FileStore, and a handler runs inside a database session that would be held open meanwhile. The composition root
builds them through module.py, with the FileStore passed in.
"""
