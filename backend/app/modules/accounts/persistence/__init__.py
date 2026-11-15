"""The accounts module's persistence: its tables (tables.py) and the write side's shared table access (repository.py).
Private to the module: only its command and query slices read or write them, and module.py hands TABLES to the
composition root for the migrations.
"""
