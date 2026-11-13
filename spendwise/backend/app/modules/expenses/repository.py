"""The only code that reads or writes the expenses table."""

from sqlmodel import Session, col, select

from app.modules.expenses.models import Expense


def add(session: Session, expense: Expense) -> Expense:
    session.add(expense)
    session.commit()
    # Reload so values the database generated (the new id) are filled in.
    session.refresh(expense)
    return expense


def list_all(session: Session) -> list[Expense]:
    # Newest first: that's how people read a list of expenses.
    # col() tells the type checker these are database columns, which have .desc().
    statement = select(Expense).order_by(col(Expense.spent_on).desc(), col(Expense.id).desc())
    return list(session.exec(statement))
