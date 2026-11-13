"""The only code that reads or writes the categories table."""

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.modules.categories.models import Category


def add(session: Session, category: Category) -> Category:
    session.add(category)
    session.commit()
    # Reload so values the database generated (the new id) are filled in.
    session.refresh(category)
    return category


def get(session: Session, category_id: int) -> Category | None:
    return session.get(Category, category_id)


def get_by_name(session: Session, name: str) -> Category | None:
    # Any letter case: "food" and "Food" are the same category to a person (and to the assistant,
    # which looks categories up case-insensitively), so they must not both exist.
    return session.exec(select(Category).where(func.lower(Category.name) == func.lower(name))).first()


def list_all(session: Session) -> list[Category]:
    return list(session.exec(select(Category).order_by(col(Category.id))))
