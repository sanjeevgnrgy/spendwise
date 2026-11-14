"""Where the approvals are stored: tables.py, the pending_approval table.

The approvals' persistence layer, private to the assistant module: store.py and the command slices read and
write the table; module.py hands its TABLES to the composition root for the migrations.
Nothing is exported here: tables.py is imported by its full path.
"""
