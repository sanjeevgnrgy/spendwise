"""The expense rules that hold however an expense is created or changed (REST, MCP, the assistant).

The expenses module's domain rules: plain functions with no database access, called by the command
handlers (commands.py) before anything is staged. Checks a schema can't express live here; checks that
need another module (the category must exist) stay in the handlers, which can ask through the bus.
"""

from decimal import Decimal

from app.core.errors import BusinessRuleError


def require_positive_amount(amount: Decimal) -> None:
    """Raise BusinessRuleError unless the amount (in rupees) is above zero."""
    # A business rule, not a format rule: zero or negative amounts aren't expenses.
    if amount <= 0:
        raise BusinessRuleError("Amount must be greater than 0")
