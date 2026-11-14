"""FindCategoryByName: the category with a given name, in any letter case. The query and its handler.

A slice of the categories module's read side; it never changes anything. module.py registers the handler with
the bus. The MCP tools ask it to turn a category name into an id, and CreateCategory (commands/create_category.py)
to spot a duplicate. The answer is a frozen CategoryRead copy (models.py), never a table row.
"""

from pydantic import ConfigDict
from sqlalchemy import func
from sqlmodel import select

from app.core.cqrs import Context, Query
from app.modules.categories.models import CategoryRead
from app.modules.categories.persistence.tables import Category
from app.modules.categories.values import CategoryName


# How a name typed by a person or a model becomes a category (the MCP tools), and how CreateCategory
# spots a duplicate. Spaces around the name are trimmed first; the letter case is compared in the
# database (find_category_by_name, below).
class FindCategoryByName(Query[CategoryRead | None]):
    """The category with this name in any letter case ("food" finds "Food"), or None."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: CategoryName


def find_category_by_name(ctx: Context, query: FindCategoryByName) -> CategoryRead | None:
    """The category whose name matches in any letter case, or None.

    The name arrives already trimmed of spaces (FindCategoryByName strips them). Only the first match is
    taken; create_category makes sure there is never more than one.
    """
    # The database lowercases both sides, so the comparison is the same wherever it's asked from.
    statement = select(Category).where(func.lower(Category.name) == func.lower(query.name))
    row = ctx.session.exec(statement).first()
    return CategoryRead.model_validate(row) if row else None
