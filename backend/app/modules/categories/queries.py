"""Query handlers: read categories straight into CategoryRead copies. They never change anything."""

from sqlalchemy import func
from sqlmodel import col, select

from app.core.cqrs import Context
from app.modules.categories.contracts import CategoryRead, FindCategoryByName, GetCategory, ListCategories
from app.modules.categories.tables import Category


def list_categories(ctx: Context, query: ListCategories) -> list[CategoryRead]:
    rows = ctx.session.exec(select(Category).order_by(col(Category.id)))
    return [CategoryRead.model_validate(row) for row in rows]


def get_category(ctx: Context, query: GetCategory) -> CategoryRead | None:
    row = ctx.session.get(Category, query.category_id)
    return CategoryRead.model_validate(row) if row else None


def find_category_by_name(ctx: Context, query: FindCategoryByName) -> CategoryRead | None:
    # The database lowercases both sides, so the comparison is the same wherever it's asked from.
    statement = select(Category).where(func.lower(Category.name) == func.lower(query.name))
    row = ctx.session.exec(statement).first()
    return CategoryRead.model_validate(row) if row else None
