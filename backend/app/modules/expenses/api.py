"""HTTP routes for expenses. Each one only translates between HTTP and commands or queries.

No business rules here, and no try/except: errors become problem-details responses in core/errors.py.
A command returns at most an id, so a route that must answer with the expense asks for it afterwards.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.core.dependencies import BusDep, ClockDep, IdPath
from app.core.money import DEFAULT_CURRENCY, CurrencyCode
from app.core.months import YearMonth
from app.modules.expenses.contracts import (
    DEFAULT_TREND_MONTHS,
    MAX_TREND_MONTHS,
    CreateExpense,
    DeleteExpense,
    ExpenseChanges,
    ExpenseList,
    ExpenseRead,
    GetExpense,
    GetMonthlySummary,
    GetMonthlyTrend,
    ListExpenses,
    MonthlySummary,
    MonthlyTrend,
    UpdateExpense,
)

router = APIRouter(tags=["expenses"])

Currency = Annotated[CurrencyCode, Query()]


@router.post("/expenses", status_code=201)
def create_expense(body: CreateExpense, bus: BusDep, request: Request, response: Response) -> ExpenseRead:
    expense_id = bus.execute(body)
    # 201 Created says where the new resource lives (url_for includes the /api/v1 prefix).
    response.headers["Location"] = str(request.url_for(get_expense.__name__, expense_id=expense_id))
    return bus.ask(GetExpense(expense_id=expense_id))


@router.get("/expenses")
def list_expenses(query: Annotated[ListExpenses, Query()], bus: BusDep) -> ExpenseList:
    return bus.ask(query)


@router.get("/expenses/{expense_id}")
def get_expense(expense_id: IdPath, bus: BusDep) -> ExpenseRead:
    return bus.ask(GetExpense(expense_id=expense_id))


@router.patch("/expenses/{expense_id}")
def update_expense(expense_id: IdPath, body: ExpenseChanges, bus: BusDep) -> ExpenseRead:
    bus.execute(UpdateExpense(expense_id=expense_id, changes=body))
    return bus.ask(GetExpense(expense_id=expense_id))


# 204 No Content: the delete worked and there's nothing left to send back.
@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: IdPath, bus: BusDep) -> None:
    bus.execute(DeleteExpense(expense_id=expense_id))


@router.get("/summary")
def monthly_summary(
    bus: BusDep,
    month: Annotated[str, Query(pattern=YearMonth.PATTERN, examples=["2026-11"])],
    currency: Currency = DEFAULT_CURRENCY,
) -> MonthlySummary:
    return bus.ask(GetMonthlySummary(month=YearMonth.parse(month), currency=currency))


@router.get("/summary/trend")
def monthly_trend(
    bus: BusDep,
    clock: ClockDep,
    months: Annotated[int, Query(ge=1, le=MAX_TREND_MONTHS)] = DEFAULT_TREND_MONTHS,
    currency: Currency = DEFAULT_CURRENCY,
) -> MonthlyTrend:
    # "The last N months" counts back from the clock's today.
    return bus.ask(GetMonthlyTrend(months=months, until=clock.today(), currency=currency))
