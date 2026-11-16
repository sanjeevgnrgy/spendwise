"""HTTP routes for expenses. Each one only translates between HTTP and commands or queries.

No business rules here, and no try/except: errors become problem-details responses in web/problems.py.
A command returns at most an id, so a route that must answer with the expense asks for it afterwards.

Every route acts for the signed-in person (`principal`, from the session): the owner of every message is their id,
never something the request says (D190). Another person's expense answers 404, like one that doesn't exist.

The expenses module's REST adapter. The composition root mounts `router` under /api/v1; the web app's
Expenses and Dashboard pages call these routes. A route's docstring would become its OpenAPI text, so
notes about the routes are `#` comments.
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.core.money import DEFAULT_CURRENCY, CurrencyCode
from app.core.months import YearMonth
from app.modules.expenses.commands.create_expense import CreateExpense, NewExpense
from app.modules.expenses.commands.delete_expense import DeleteExpense
from app.modules.expenses.commands.update_expense import ExpenseChanges, UpdateExpense
from app.modules.expenses.models import ExpenseList, ExpenseRead
from app.modules.expenses.queries.get_expense import GetExpense
from app.modules.expenses.queries.get_monthly_summary import GetMonthlySummary, MonthlySummary
from app.modules.expenses.queries.get_monthly_trend import GetMonthlyTrend, MonthlyTrend
from app.modules.expenses.queries.list_expenses import ExpenseFilters, ListExpenses
from app.modules.expenses.values import DEFAULT_TREND_MONTHS, MAX_TREND_MONTHS
from app.web.auth import CurrentUserDep
from app.web.dependencies import BusDep, ClockDep, IdPath

router = APIRouter(tags=["expenses"])

# A currency code as a query parameter (?currency=INR), with the same pattern as in bodies.
Currency = Annotated[CurrencyCode, Query()]


# POST /api/v1/expenses: record an expense for the signed-in person; the body is NewExpense. A malformed body is a
# 422 "validation" problem; an amount <= 0 or an unknown category, a 422 "business-rule" one.
@router.post("/expenses", status_code=201)
def create_expense(
    body: NewExpense, principal: CurrentUserDep, bus: BusDep, request: Request, response: Response
) -> ExpenseRead:
    owner = principal.user_id
    expense_id = bus.execute(CreateExpense(owner_id=owner, expense=body))
    # 201 Created says where the new resource lives (url_for includes the /api/v1 prefix).
    response.headers["Location"] = str(request.url_for(get_expense.__name__, expense_id=expense_id))
    return bus.ask(GetExpense(owner_id=owner, expense_id=expense_id))


# GET /api/v1/expenses: one page of the signed-in person's expenses, newest first; the query parameters are
# ExpenseFilters's fields, so an unknown parameter is a 422 instead of being ignored.
@router.get("/expenses")
def list_expenses(filters: Annotated[ExpenseFilters, Query()], principal: CurrentUserDep, bus: BusDep) -> ExpenseList:
    return bus.ask(ListExpenses(owner_id=principal.user_id, filters=filters))


# GET /api/v1/expenses/{id}: one of the signed-in person's expenses; a 404 problem if they have no such expense.
@router.get("/expenses/{expense_id}")
def get_expense(expense_id: IdPath, principal: CurrentUserDep, bus: BusDep) -> ExpenseRead:
    return bus.ask(GetExpense(owner_id=principal.user_id, expense_id=expense_id))


# PATCH /api/v1/expenses/{id}: change only the fields sent ("note": null clears the note); every update
# raises the expense's version. Answers with the expense as it is now; 404 if it isn't the person's.
@router.patch("/expenses/{expense_id}")
def update_expense(expense_id: IdPath, body: ExpenseChanges, principal: CurrentUserDep, bus: BusDep) -> ExpenseRead:
    owner = principal.user_id
    bus.execute(UpdateExpense(owner_id=owner, expense_id=expense_id, changes=body))
    return bus.ask(GetExpense(owner_id=owner, expense_id=expense_id))


# DELETE /api/v1/expenses/{id}: delete for good, without a version check (the web app's dialog asks
# first). 204 No Content: the delete worked and there's nothing left to send back. 404 if it isn't the person's.
@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: IdPath, principal: CurrentUserDep, bus: BusDep) -> None:
    bus.execute(DeleteExpense(owner_id=principal.user_id, expense_id=expense_id))


# GET /api/v1/summary?month=2026-11: one month's total of the signed-in person's expenses and per-category totals,
# added up in the database, in one currency (INR unless asked otherwise).
@router.get("/summary")
def monthly_summary(
    principal: CurrentUserDep,
    bus: BusDep,
    month: Annotated[str, Query(pattern=YearMonth.PATTERN, examples=["2026-11"])],
    currency: Currency = DEFAULT_CURRENCY,
) -> MonthlySummary:
    return bus.ask(GetMonthlySummary(owner_id=principal.user_id, month=YearMonth.parse(month), currency=currency))


# GET /api/v1/summary/trend?months=6: the Dashboard chart's monthly totals, oldest first, with 0 for a
# month without spending.
@router.get("/summary/trend")
def monthly_trend(
    principal: CurrentUserDep,
    bus: BusDep,
    clock: ClockDep,
    months: Annotated[int, Query(ge=1, le=MAX_TREND_MONTHS)] = DEFAULT_TREND_MONTHS,
    currency: Currency = DEFAULT_CURRENCY,
) -> MonthlyTrend:
    # "The last N months" counts back from the clock's today.
    query = GetMonthlyTrend(owner_id=principal.user_id, months=months, until=clock.today(), currency=currency)
    return bus.ask(query)
