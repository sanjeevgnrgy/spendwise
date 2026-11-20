"""The expenses module's use case that isn't a bus message (application/): ExpenseRecorder (record_expense.py), which
fetches a rate before saving an expense in another currency, since no network call may happen inside a unit of work.
The composition root builds it through module.py, with the exchange rates passed in.
"""
