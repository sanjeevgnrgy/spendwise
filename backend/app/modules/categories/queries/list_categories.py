"""ListCategories: every category, oldest first. The query and its handler; it never changes anything.

A slice of the categories module's read side. module.py registers the handler with the bus; callers send the
query (bus.ask(ListCategories())) and get frozen CategoryRead copies, never table rows they could change. Asked by
GET /categories (api.py), the expenses module's summaries, the MCP tools, the assistant and seed.py.
"""

from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.modules.categories.models import CategoryRead
from app.modules.categories.persistence.tables import Category


# Answers GET /categories, names the categories in summaries and MCP results, and gives the assistant
# and seed.py the list.
class ListCategories(Query[list[CategoryRead]]):
    """Every category, in the order they were created."""


def list_categories(ctx: Context, query: ListCategories) -> list[CategoryRead]:
    """Every category, oldest first (ids grow as categories are added, so id order is creation order)."""
    rows = ctx.session.exec(select(Category).order_by(col(Category.id)))
    return [CategoryRead.model_validate(row) for row in rows]
