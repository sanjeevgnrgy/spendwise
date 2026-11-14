"""GetCategory: one category by id, or None. The query and its handler; it never changes anything.

A slice of the categories module's read side. module.py registers the handler with the bus. The expenses module
asks it whether an expense's category exists (there is no foreign key), and the MCP tools to name one expense's
category. The answer is a frozen CategoryRead copy (models.py), never a table row.
"""

from app.core.cqrs import Context, Query
from app.modules.categories.models import CategoryRead
from app.modules.categories.persistence.tables import Category
from app.modules.categories.values import CategoryId


# The expenses module's "does this category exist?" check before it saves an expense (there is no
# foreign key to do it). The MCP tools also use it to name one expense's category.
class GetCategory(Query[CategoryRead | None]):
    """One category, or None if it doesn't exist (callers use it as a "does it exist?" check)."""

    category_id: CategoryId


def get_category(ctx: Context, query: GetCategory) -> CategoryRead | None:
    """One category by id, or None if there's no such category (not an error: callers decide)."""
    row = ctx.session.get(Category, query.category_id)
    return CategoryRead.model_validate(row) if row else None
