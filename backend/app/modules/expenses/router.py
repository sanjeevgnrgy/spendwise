"""HTTP routes for expenses. Each one only translates between HTTP and a service call.

No business rules here, and no try/except: service errors become 404/422 in core/errors.py.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.core.db import MAX_ID, SessionDep
from app.core.money import DEFAULT_CURRENCY
from app.modules.expenses import service
from app.modules.expenses.schemas import (
    MONTH_PATTERN,
    ExpenseCreate,
    ExpenseFilters,
    ExpenseRead,
    ExpenseUpdate,
    MonthlySummary,
    MonthlyTrend,
)

router = APIRouter(tags=["expenses"])

# An id the database could hold; anything bigger is a 422, not a driver crash (see core/db.py).
ExpenseId = Annotated[int, Path(ge=1, le=MAX_ID)]


@router.post("/expenses", status_code=201)
def create_expense(body: ExpenseCreate, session: SessionDep) -> ExpenseRead:
    return service.create_expense(session, body)


@router.get("/expenses")
def list_expenses(filters: Annotated[ExpenseFilters, Query()], session: SessionDep) -> list[ExpenseRead]:
    return service.list_expenses(session, filters)


@router.get("/expenses/{expense_id}")
def get_expense(expense_id: ExpenseId, session: SessionDep) -> ExpenseRead:
    return service.get_expense(session, expense_id)


@router.patch("/expenses/{expense_id}")
def update_expense(expense_id: ExpenseId, body: ExpenseUpdate, session: SessionDep) -> ExpenseRead:
    return service.update_expense(session, expense_id, body)


# 204 No Content: the delete worked and there's nothing left to send back.
@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: ExpenseId, session: SessionDep) -> None:
    service.delete_expense(session, expense_id)


@router.get("/summary")
def monthly_summary(
    session: SessionDep,
    month: Annotated[str, Query(pattern=MONTH_PATTERN, examples=["2026-11"])],
    # Totals only make sense within one currency, so the summary covers one at a time.
    currency: Annotated[str, Query(pattern=r"^[A-Z]{3}$")] = DEFAULT_CURRENCY,
) -> MonthlySummary:
    year, month_number = (int(part) for part in month.split("-"))
    return service.monthly_summary(session, year, month_number, currency)


@router.get("/summary/trend")
def monthly_trend(
    session: SessionDep,
    # Capped at 24 so one request can't ask the database for decades of grouping.
    months: Annotated[int, Query(ge=1, le=24)] = 6,
    currency: Annotated[str, Query(pattern=r"^[A-Z]{3}$")] = DEFAULT_CURRENCY,
) -> MonthlyTrend:
    # "The last N months" counts back from the server's today (like /parse and /chat do).
    return service.monthly_trend(session, months, date.today(), currency)
