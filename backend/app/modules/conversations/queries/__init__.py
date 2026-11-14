"""The conversations module's queries, one file each: the query message, its handler and what only it uses, plus
thread_rows.py, the row reading that GetHistory and GetThread share. Handlers return neutral messages or readable
copies, never table rows, and never change anything. module.py registers each handler with the bus.
"""
