"""Expenses in other currencies: the ExchangeRates port (port.py) and its adapter (currency_agent.py), which asks the
currency agent (agents/currency) through the remote-agents port (core/agents.py). The recorder
(application/record_expense.py) uses the port; the composition root builds the adapter through module.py (D204).
"""
