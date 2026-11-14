"""CreateCategory: add a category. The command and its handler, the only code that adds categories.

A slice of the categories module's write side. module.py registers the handler with the bus, and callers reach it
only by sending the command (bus.execute(CreateCategory(...))), never by calling it directly; seed.py is the one
sender today. To spot a duplicate it sends FindCategoryByName (queries/). The bus commits; the handler never does.
"""

from pydantic import ConfigDict

from app.core.cqrs import Command, Context
from app.core.errors import BusinessRuleError
from app.modules.categories.persistence.tables import Category
from app.modules.categories.queries.find_category_by_name import FindCategoryByName
from app.modules.categories.values import CategoryName, IconName


# Add a category (seed.py does; there's no REST route for it yet). The handler refuses a name that
# already exists in any letter case, with a BusinessRuleError (create_category, below).
class CreateCategory(Command[int]):
    """Returns the new category's id."""

    # Trim stray spaces from both fields before they're checked and stored.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: CategoryName
    icon: IconName


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
