"""Business rules for expenses. Returns DTOs (ExpenseRead), never table rows."""

from sqlmodel import Session

# The categories module's public interface: the only way in to another module.
from app.modules import categories
from app.modules.expenses import repository
from app.modules.expenses.models import Expense
from app.modules.expenses.schemas import ExpenseCreate, ExpenseRead


def create_expense(session: Session, data: ExpenseCreate) -> ExpenseRead:
    # Ask the categories module whether the category exists, instead of reading its table.
    if categories.get_category(session, data.category_id) is None:
        raise ValueError(f"Category {data.category_id} does not exist")
    expense = repository.add(session, Expense(**data.model_dump()))
    return ExpenseRead.model_validate(expense)


def list_expenses(session: Session) -> list[ExpenseRead]:
    return [ExpenseRead.model_validate(e) for e in repository.list_all(session)]
