"""Query handlers: read categories straight into CategoryRead copies. They never change anything.

Part of the categories module's read side. module.py registers each handler with the bus; callers send
the query (bus.ask(GetCategory(...))) and get frozen copies, never table rows they could change.
"""

from sqlalchemy import func
from sqlmodel import col, select

from app.core.cqrs import Context
from app.modules.categories.contracts import CategoryRead, FindCategoryByName, GetCategory, ListCategories
from app.modules.categories.tables import Category


def list_categories(ctx: Context, query: ListCategories) -> list[CategoryRead]:
    """Every category, oldest first (ids grow as categories are added, so id order is creation order)."""
    rows = ctx.session.exec(select(Category).order_by(col(Category.id)))
    return [CategoryRead.model_validate(row) for row in rows]


def get_category(ctx: Context, query: GetCategory) -> CategoryRead | None:
    """One category by id, or None if there's no such category (not an error: callers decide)."""
    row = ctx.session.get(Category, query.category_id)
    return CategoryRead.model_validate(row) if row else None


def find_category_by_name(ctx: Context, query: FindCategoryByName) -> CategoryRead | None:
    """The category whose name matches in any letter case, or None.

    The name arrives already trimmed of spaces (FindCategoryByName strips them). Only the first match is
    taken; create_category makes sure there is never more than one.
    """
    # The database lowercases both sides, so the comparison is the same wherever it's asked from.
    statement = select(Category).where(func.lower(Category.name) == func.lower(query.name))
    row = ctx.session.exec(statement).first()
    return CategoryRead.model_validate(row) if row else None
