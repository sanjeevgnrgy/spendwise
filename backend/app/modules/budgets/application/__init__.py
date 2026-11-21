"""The budgets module's use case that isn't a bus message (application/): BudgetWatch, which looks at a save's month
before and after it. Not a handler: the save in between may wait for an exchange rate, and a handler runs inside a
database session that would be held open meanwhile. The composition root builds it through module.py.
"""
