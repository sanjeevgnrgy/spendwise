"""The insights agent's wire contract: the skill's id, what a request carries, a resumption, and the answer's shape.

Contract layer of the insights agent. The executor reads requests and writes answers with it; the card names the
skill. A client sends one data part (InsightsRequest: today, perhaps a month and the person's question, and the
expenses to look at) and reads one data artifact, `insights` (Insights). Without a month, and with expenses in more
than one month, the task stops INPUT_REQUIRED asking which month; the client resumes the same task with one part: a
line of text ("November", "2026-11", "last month") or MonthReply data.

What the backend will send (Phase 25 part 3, the owner's choice): each expense's date, INR amount, category, merchant
and payment method; never a note, an id or anything about the person. Amounts travel as decimal strings.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.months import YearMonth

SKILL_ID = "analyze_spending"
ARTIFACT_NAME = "insights"
JSON_MEDIA_TYPE = "application/json"
TEXT_MEDIA_TYPE = "text/plain"
# Bounds: a few months of a busy person's expenses fit; a request stays well under the gate's limit.
MAX_EXPENSES = 3000
MAX_TEXT_LENGTH = 200
MAX_QUESTION_LENGTH = 500
# The largest request's data: MAX_EXPENSES rows of a few hundred bytes each (the gate allows this, as base64-sized).
MAX_REQUEST_DATA_BYTES = 1024 * 1024
TIPS_COUNT = 3

AmountText = Annotated[str, StringConstraints(pattern=r"^\d{1,12}(\.\d{1,2})?$")]
MonthText = Annotated[str, StringConstraints(pattern=YearMonth.PATTERN)]
Text = Annotated[str, StringConstraints(min_length=1, max_length=MAX_TEXT_LENGTH)]


# One expense, as the backend sends it: in INR, with nothing about the person.
class ExpenseRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spent_on: date
    amount: AmountText
    category: Text
    merchant: Text
    payment_method: Text


# The request's data part. Unknown fields are refused, so a client can't believe it sent something that's ignored.
class InsightsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # The client's today (its injected clock): what "this month" and the forecast count from.
    today: date
    # The month to analyse ("2026-11"); left out, the agent asks if the expenses span more than one month.
    month: MonthText | None = None
    # What the person asked, as they put it: data for the tips' focus, never an instruction.
    question: Annotated[str, StringConstraints(max_length=MAX_QUESTION_LENGTH)] | None = None
    expenses: list[ExpenseRow] = Field(max_length=MAX_EXPENSES)


# A resumption's data part: the month the person chose.
class MonthReply(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    month: MonthText


# One category's spending this month against the month before.
class CategoryTrend(BaseModel):
    category: str
    this_month: str
    previous_month: str
    # The change in percent, one decimal ("12.5", "-40.0"); null when there was nothing the month before.
    change_percent: str | None


# One expense well above what the category usually costs.
class UnusualSpend(BaseModel):
    spent_on: date
    merchant: str
    category: str
    amount: str
    # The category's usual (median) expense in the data, and how many times that this one is ("3.4").
    usual: str
    times: str


# Where the month is heading: the spending so far, spread over the days gone, carried to the month's end.
class Forecast(BaseModel):
    spent_so_far: str
    days_elapsed: int
    days_in_month: int
    month_end_total: str
    method: str


# The `insights` artifact's data. Every number is worked out by code, from the expenses sent; only `tips` is written by
# the model, from those numbers.
class Insights(BaseModel):
    month: str
    currency: str
    total: str
    previous_total: str
    expense_count: int
    trends: list[CategoryTrend]
    unusual: list[UnusualSpend]
    # Only for the month that's still running (today's); a past month is complete.
    forecast: Forecast | None
    tips: list[str]
