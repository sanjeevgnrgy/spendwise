"""The expense rules that hold however an expense is created or changed (REST, MCP, the assistant).

The expenses module's domain rules, shared by the CreateExpense and UpdateExpense slices (commands/), which call
them before anything is staged. Checks a schema can't express live here. require_positive_amount is a plain
function with no database access; require_category_exists needs another module, so it asks that module through
the bus (the handler's Context), never by reading its table.
"""

from decimal import Decimal

from app.core.cqrs import Context
from app.core.errors import BusinessRuleError
from app.modules import categories


def require_positive_amount(amount: Decimal) -> None:
    """Raise BusinessRuleError unless the amount (in rupees) is above zero."""
    # A business rule, not a format rule: zero or negative amounts aren't expenses.
    if amount <= 0:
        raise BusinessRuleError("Amount must be greater than 0")


def require_category_exists(ctx: Context, category_id: int) -> None:
    """Raise BusinessRuleError unless the category exists.

    expense.category_id has no foreign key (each module owns its tables), so this check is what keeps
    an expense from pointing at a category that isn't there.
    """
    # Ask the categories module, through its contract, instead of reading its table.
    if ctx.bus.ask(categories.GetCategory(category_id=category_id)) is None:
        raise BusinessRuleError(f"Category {category_id} does not exist")
