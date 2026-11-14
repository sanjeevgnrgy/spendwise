"""The receipts module's use cases that aren't bus messages (application/): uploading a receipt (saving its bytes,
then recording it) and reading one with the model. Neither is a handler: one writes a file, the other calls the
model, and a handler runs inside a database session that would be held open meanwhile. The composition root builds
them through module.py, with the FileStore and the model passed in.
"""
