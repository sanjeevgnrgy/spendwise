"""Command handlers: the only code that changes categories. The bus commits; handlers never do.

Part of the categories module's write side. module.py registers each handler with the bus, and callers
reach it only by sending the command (bus.execute(CreateCategory(...))), never by calling it directly.
"""

from app.core.cqrs import Context
from app.core.errors import BusinessRuleError
from app.modules.categories.contracts import CreateCategory, FindCategoryByName
from app.modules.categories.tables import Category


def create_category(ctx: Context, command: CreateCategory) -> int:
    """Add a category and return its new id.

    Raises BusinessRuleError if a category with the same name already exists, ignoring letter case and
    spaces around it ("food " and "Food" are the same). The row is only staged and flushed here; the
    bus commits it when the command finishes.
    """
    # Checked here, not only by the unique index, to give a clear message instead of a SQL error.
    # Any letter case: "food" and "Food" are the same category to a person (and to the assistant).
    # The check is a query through the bus, so it runs in this command's own transaction.
    if ctx.bus.ask(FindCategoryByName(name=command.name)) is not None:
        raise BusinessRuleError(f"Category '{command.name}' already exists")
    category = Category(name=command.name, icon=command.icon)
    ctx.session.add(category)
    # flush sends the INSERT inside the transaction, so the database assigns the id now.
    ctx.session.flush()
    assert category.id is not None
    return category.id
