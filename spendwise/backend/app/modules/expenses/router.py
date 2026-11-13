"""HTTP routes for expenses. Each one only translates between HTTP and a service call.

No business rules here, and no try/except: service errors become 404/422 in core/errors.py.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.db import SessionDep
from app.core.money import DEFAULT_CURRENCY
from app.modules.expenses import service
from app.modules.expenses.schemas import ExpenseCreate, ExpenseFilters, ExpenseRead, ExpenseUpdate, MonthlySummary

router = APIRouter(tags=["expenses"])


@router.post("/expenses", status_code=201)
def create_expense(body: ExpenseCreate, session: SessionDep) -> ExpenseRead:
    return service.create_expense(session, body)


@router.get("/expenses")
def list_expenses(filters: Annotated[ExpenseFilters, Query()], session: SessionDep) -> list[ExpenseRead]:
    return service.list_expenses(session, filters)


@router.get("/expenses/{expense_id}")
def get_expense(expense_id: int, session: SessionDep) -> ExpenseRead:
    return service.get_expense(session, expense_id)


@router.patch("/expenses/{expense_id}")
def update_expense(expense_id: int, body: ExpenseUpdate, session: SessionDep) -> ExpenseRead:
    return service.update_expense(session, expense_id, body)


# 204 No Content: the delete worked and there's nothing left to send back.
@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, session: SessionDep) -> None:
    service.delete_expense(session, expense_id)


@router.get("/summary")
def monthly_summary(
    session: SessionDep,
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-11"])],
    # Totals only make sense within one currency, so the summary covers one at a time.
    currency: Annotated[str, Query(pattern=r"^[A-Z]{3}$")] = DEFAULT_CURRENCY,
) -> MonthlySummary:
    year, month_number = (int(part) for part in month.split("-"))
    return service.monthly_summary(session, year, month_number, currency)
