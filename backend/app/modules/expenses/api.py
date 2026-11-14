"""HTTP routes for expenses. Each one only translates between HTTP and commands or queries.

No business rules here, and no try/except: errors become problem-details responses in core/errors.py.
A command returns at most an id, so a route that must answer with the expense asks for it afterwards.

The expenses module's REST adapter. The composition root mounts `router` under /api/v1; the web app's
Expenses and Dashboard pages call these routes. A route's docstring would become its OpenAPI text, so
notes about the routes are `#` comments.
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

# A currency code as a query parameter (?currency=INR), with the same pattern as in bodies.
Currency = Annotated[CurrencyCode, Query()]


# POST /api/v1/expenses: record an expense; the body is the CreateExpense command itself. A malformed
# body is a 422 "validation" problem; an amount <= 0 or an unknown category, a 422 "business-rule" one.
@router.post("/expenses", status_code=201)
def create_expense(body: CreateExpense, bus: BusDep, request: Request, response: Response) -> ExpenseRead:
    expense_id = bus.execute(body)
    # 201 Created says where the new resource lives (url_for includes the /api/v1 prefix).
    response.headers["Location"] = str(request.url_for(get_expense.__name__, expense_id=expense_id))
    return bus.ask(GetExpense(expense_id=expense_id))


# GET /api/v1/expenses: one page of expenses, newest first; the query parameters are ListExpenses's
# fields, so an unknown parameter is a 422 instead of being ignored.
@router.get("/expenses")
def list_expenses(query: Annotated[ListExpenses, Query()], bus: BusDep) -> ExpenseList:
    return bus.ask(query)


# GET /api/v1/expenses/{id}: one expense; 404 problem if there's no such expense.
@router.get("/expenses/{expense_id}")
def get_expense(expense_id: IdPath, bus: BusDep) -> ExpenseRead:
    return bus.ask(GetExpense(expense_id=expense_id))


# PATCH /api/v1/expenses/{id}: change only the fields sent ("note": null clears the note); every update
# raises the expense's version. Answers with the expense as it is now.
@router.patch("/expenses/{expense_id}")
def update_expense(expense_id: IdPath, body: ExpenseChanges, bus: BusDep) -> ExpenseRead:
    bus.execute(UpdateExpense(expense_id=expense_id, changes=body))
    return bus.ask(GetExpense(expense_id=expense_id))


# DELETE /api/v1/expenses/{id}: delete for good, without a version check (the web app's dialog asks
# first). 204 No Content: the delete worked and there's nothing left to send back.
@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: IdPath, bus: BusDep) -> None:
    bus.execute(DeleteExpense(expense_id=expense_id))


# GET /api/v1/summary?month=2026-11: one month's total and per-category totals, added up in the
# database, in one currency (INR unless asked otherwise).
@router.get("/summary")
def monthly_summary(
    bus: BusDep,
    month: Annotated[str, Query(pattern=YearMonth.PATTERN, examples=["2026-11"])],
    currency: Currency = DEFAULT_CURRENCY,
) -> MonthlySummary:
    return bus.ask(GetMonthlySummary(month=YearMonth.parse(month), currency=currency))


# GET /api/v1/summary/trend?months=6: the Dashboard chart's monthly totals, oldest first, with 0 for a
# month without spending.
@router.get("/summary/trend")
def monthly_trend(
    bus: BusDep,
    clock: ClockDep,
    months: Annotated[int, Query(ge=1, le=MAX_TREND_MONTHS)] = DEFAULT_TREND_MONTHS,
    currency: Currency = DEFAULT_CURRENCY,
) -> MonthlyTrend:
    # "The last N months" counts back from the clock's today.
    return bus.ask(GetMonthlyTrend(months=months, until=clock.today(), currency=currency))
