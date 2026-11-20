"""Budgets module: a person's monthly spending limits, overall and per category, and how a month measures up.

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.budgets`, and send them through the bus. Tables, handlers, the repository and the router stay private;
the composition root (bootstrap.py) plugs them in through module.py.

A budget is a standing monthly limit in INR: the same every month until it's changed. Spending comes from the
expenses module's monthly summary (every currency at its INR amount, D204), category names from the categories
module: this module stores only the limits. Every command and query names its owner (D190).

Depends on: expenses, categories. Who uses it: the composition root (its routes), the web contract (BudgetState and
the thresholds), the MCP tools (get_budgets and set_budget; add_expense and update_expense, for the alerts crossed()
finds) and the assistant (the budget card, and the alerts on the expense card).
"""

from app.modules.budgets.commands.remove_budget import RemoveBudget
from app.modules.budgets.commands.set_budget import BudgetChange, SetBudget
from app.modules.budgets.domain.alerts import crossed
from app.modules.budgets.models import BudgetAlert
from app.modules.budgets.queries.get_budget_status import BudgetLine, BudgetStatus, CategoryBudgetLine, GetBudgetStatus
from app.modules.budgets.values import FULL_PERCENT, NEAR_LIMIT_PERCENT, BudgetLimit, BudgetState

__all__ = [
    "FULL_PERCENT",
    "NEAR_LIMIT_PERCENT",
    "BudgetAlert",
    "BudgetChange",
    "BudgetLimit",
    "BudgetLine",
    "BudgetState",
    "BudgetStatus",
    "CategoryBudgetLine",
    "GetBudgetStatus",
    "RemoveBudget",
    "SetBudget",
    "crossed",
]
