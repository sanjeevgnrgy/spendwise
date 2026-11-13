"""The expense rules that hold however an expense is created or changed (REST, MCP, the assistant)."""

from decimal import Decimal

from app.core.errors import BusinessRuleError


def require_positive_amount(amount: Decimal) -> None:
    # A business rule, not a format rule: zero or negative amounts aren't expenses.
    if amount <= 0:
        raise BusinessRuleError("Amount must be greater than 0")
