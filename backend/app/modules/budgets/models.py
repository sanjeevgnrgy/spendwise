"""The budgets module's shared read model: BudgetAlert, a budget a change pushed near or over its limit.

Part of the module's contract layer. domain/alerts.py builds alerts by comparing two statuses; the MCP tools that save
expenses (add_expense, update_expense) send them in their results, and the assistant's expense card shows them. It's
an MCP result, so notes are `#` comments (a docstring would be published schema text).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.modules.budgets.values import BudgetState


# A budget that a save moved into a worse state: near its limit (from 80%) or over it. `category` is the category's
# name, or null for the overall budget (the whole month).
class BudgetAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str | None
    state: BudgetState
    spent: Decimal
    limit: Decimal
    used_percent: Decimal
