"""The receipts module's persistence: its table (tables.py). Private to the module: only its command and query slices
read or write it, and module.py hands TABLES to the composition root for the migrations. The files' bytes aren't
here: they're in the FileStore (core/files.py), and the table keeps their keys.
"""
