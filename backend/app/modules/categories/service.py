"""Business rules for categories. Returns DTOs (CategoryRead), never table rows."""

from sqlmodel import Session

from app.core.errors import BusinessRuleError
from app.modules.categories import repository
from app.modules.categories.models import Category
from app.modules.categories.schemas import CategoryCreate, CategoryRead


def create_category(session: Session, data: CategoryCreate) -> CategoryRead:
    # Checked here, not only by the database, to give a clear message instead of a SQL error.
    if repository.get_by_name(session, data.name) is not None:
        raise BusinessRuleError(f"Category '{data.name}' already exists")
    category = repository.add(session, Category(name=data.name, icon=data.icon))
    return CategoryRead.model_validate(category)


def get_category(session: Session, category_id: int) -> CategoryRead | None:
    # Returns None rather than raising: callers like expenses use it as a "does it exist?" check.
    category = repository.get(session, category_id)
    return CategoryRead.model_validate(category) if category else None


def list_categories(session: Session) -> list[CategoryRead]:
    return [CategoryRead.model_validate(c) for c in repository.list_all(session)]
