"""The reports module's read model: MonthlyReport, a month's figures as the skill's script works them out (D209).

Part of the module's contract layer. The use case (application/monthly_reports.py) validates the script's JSON
answer into it, so nothing the script writes reaches anyone unchecked; the routes (api.py) send it, the MCP tool
get_monthly_report answers with it, and the assistant draws its card from it. It's a REST response and an MCP result,
so its docstrings would be published schema text: notes are `#` comments.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.months import YearMonth
from app.modules import categories, expenses
from app.modules.reports.values import MAX_BIGGEST, MAX_BREAKDOWN_LINES

# An amount in INR rupees, to the paisa (the script rounds half up). Never negative: expenses are positive amounts.
Rupees = Annotated[Decimal, Field(ge=0, decimal_places=2, allow_inf_nan=False)]
# A share of the month's total, in percent, to one decimal.
Share = Annotated[Decimal, Field(ge=0, le=100, decimal_places=1, allow_inf_nan=False)]
CategoryName = Annotated[str, Field(min_length=1, max_length=categories.MAX_NAME_LENGTH)]


class _Figures(BaseModel):
    # Frozen, and a key the script shouldn't write is an error rather than something passed on.
    model_config = ConfigDict(frozen=True, extra="forbid")


# One category's part of the month: its total, how many expenses, and its share of the month's total.
class CategoryShare(_Figures):
    category: CategoryName
    total: Rupees
    count: int = Field(ge=1)
    share_percent: Share | None


# The same for one payment method.
class PaymentShare(_Figures):
    payment_method: expenses.PaymentMethod
    total: Rupees
    count: int = Field(ge=1)
    share_percent: Share | None


# One of the month's biggest expenses.
class BigExpense(_Figures):
    spent_on: date
    merchant: str = Field(min_length=1, max_length=expenses.MAX_MERCHANT_LENGTH)
    category: CategoryName
    amount: Rupees


# A month's report: the total in INR against the month before (change_percent is null when the month before had
# nothing to compare with), the daily average over the days counted (the days so far, for the running month),
# the breakdowns by category and payment method (biggest first) and the biggest expenses.
class MonthlyReport(_Figures):
    month: str = Field(pattern=YearMonth.PATTERN, examples=["2026-11"])
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    total: Rupees
    previous_total: Rupees
    change_percent: Decimal | None = Field(decimal_places=1, allow_inf_nan=False)
    expense_count: int = Field(ge=0)
    days_counted: int = Field(ge=1, le=31)
    daily_average: Rupees
    by_category: list[CategoryShare] = Field(max_length=MAX_BREAKDOWN_LINES)
    by_payment_method: list[PaymentShare] = Field(max_length=MAX_BREAKDOWN_LINES)
    biggest: list[BigExpense] = Field(max_length=MAX_BIGGEST)
