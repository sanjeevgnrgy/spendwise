"""The receipts module's queries, one file each: the query message and its handler. Handlers read rows into frozen
copies (models.py) and never change anything. module.py registers each handler with the bus; the package's
__init__.py exports the messages.
"""
