"""Command handlers: the only code that changes categories. The bus commits; handlers never do."""

from app.core.cqrs import Context
from app.core.errors import BusinessRuleError
from app.modules.categories.contracts import CreateCategory, FindCategoryByName
from app.modules.categories.tables import Category


def create_category(ctx: Context, command: CreateCategory) -> int:
    # Checked here, not only by the unique index, to give a clear message instead of a SQL error.
    # Any letter case: "food" and "Food" are the same category to a person (and to the assistant).
    if ctx.bus.ask(FindCategoryByName(name=command.name)) is not None:
        raise BusinessRuleError(f"Category '{command.name}' already exists")
    category = Category(name=command.name, icon=command.icon)
    ctx.session.add(category)
    # flush sends the INSERT inside the transaction, so the database assigns the id now.
    ctx.session.flush()
    assert category.id is not None
    return category.id
