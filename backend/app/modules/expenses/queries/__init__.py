"""The expenses module's queries, one file each: the query message, its handler, its result models and what only
it uses, plus month_range.py, the date-and-currency filter the summary and trend share. The database does the
filtering, counting and adding up, so only results travel to Python; handlers never change anything. module.py
registers each handler with the bus; the package's __init__.py exports the messages and results.
"""
