"""The skills the assistant may hand to another agent, and how: what the server sends, and how it reads the answer.

Part of the delegation. Only a skill listed here is offered to the model (AgentDirectory keeps the ones the agents'
cards really offer), because the server, not the model, decides what each agent is sent (D206):

- insights / analyze_spending: the person's expenses for the three months up to the one asked about, each as its date,
  INR amount, category, merchant and payment method (no note, id or anything about the person: the owner's choice),
  with the month (if the model passed one) and the request as the question;
- currency / convert_currency: the model's request as one line of text ("4 USD to INR").

Each answer is outside data: it's validated against the assistant's own view of it before the model sees it.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.agents import DataPart, Part, TextPart
from app.core.cqrs import MessageBus
from app.core.months import YearMonth
from app.modules import categories, expenses

# The months of expenses sent with a request for insights: the month asked about and the two before it (trends).
INSIGHTS_MONTHS = 3
# At most this many rows are sent (the insights agent's own limit is 3,000), fetched a page at a time.
MAX_INSIGHT_ROWS = 3000
# The pseudo tool names the chips are shown under (api/chip_labels.py gives each its texts).
ASK_INSIGHTS = "ask_insights_agent"
ASK_CURRENCY = "ask_currency_agent"
MAX_TEXT = 300


@dataclass(frozen=True)
class DelegationRequest:
    """What the model asked for: the request (its words), the month if it named one, and whose data it's about."""

    owner_id: int
    request: str
    month: YearMonth | None
    today: date


class DelegatedSkill(Protocol):
    """One skill the server knows how to hand over: its agent and skill ids, its artifact, its chip, and the two
    directions of the conversation."""

    agent: str
    skill_id: str
    artifact: str
    chip: str

    def parts(self, request: DelegationRequest) -> list[Part]:
        """What the agent is sent for `request` (the person's data added by the server, never by the model)."""
        ...

    def answer(self, data: list[Any]) -> dict[str, Any] | None:
        """The artifact's data, checked, as the model will read it; None if it isn't one usable answer."""
        ...


# The insights agent's answer, as the assistant accepts it. Whole numbers may arrive as floats (30.0): Pydantic reads
# them as ints. Fields it doesn't know are ignored.
class _Insights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    month: str = Field(max_length=MAX_TEXT)
    total: str = Field(max_length=MAX_TEXT)
    previous_total: str = Field(max_length=MAX_TEXT)
    expense_count: int
    trends: list[dict[str, Any]] = Field(max_length=20)
    unusual: list[dict[str, Any]] = Field(max_length=20)
    forecast: dict[str, Any] | None
    tips: list[str] = Field(max_length=5)


# The currency agent's answer, as the assistant accepts it.
class _Conversion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    amount: str = Field(max_length=MAX_TEXT)
    from_currency: str = Field(max_length=MAX_TEXT)
    to_currency: str = Field(max_length=MAX_TEXT)
    rate: str = Field(max_length=MAX_TEXT)
    rate_date: date
    converted: str = Field(max_length=MAX_TEXT)


def _one(model: type[BaseModel], data: list[Any]) -> dict[str, Any] | None:
    """The single data part validated against `model`, as JSON-ready data; None if there isn't exactly one valid."""
    if len(data) != 1:
        return None
    try:
        return model.model_validate(data[0]).model_dump(mode="json")
    except ValidationError:
        return None


@dataclass(frozen=True)
class InsightsSkill:
    """insights / analyze_spending: sends the person's recent expenses, reads the insights."""

    bus: MessageBus
    agent: str = "insights"
    skill_id: str = "analyze_spending"
    artifact: str = "insights"
    chip: str = ASK_INSIGHTS

    def parts(self, request: DelegationRequest) -> list[Part]:
        """One InsightsRequest: today, the month (if named), the request as the question, and the expenses."""
        anchor = request.month or YearMonth.of(request.today)
        start = anchor.shift(-(INSIGHTS_MONTHS - 1)).first_day()
        end = min(anchor.shift(1).first_day() - timedelta(days=1), request.today)
        data = {
            "today": request.today.isoformat(),
            "month": None if request.month is None else str(request.month),
            "question": request.request,
            "expenses": self._rows(request.owner_id, start, end),
        }
        return [DataPart(data={key: value for key, value in data.items() if value is not None})]

    def _rows(self, owner_id: int, start: date, end: date) -> list[dict[str, str]]:
        """The owner's expenses in [start, end] with an INR amount, as the agent's rows (no note, id or person)."""
        names = {category.id: category.name for category in self.bus.ask(categories.ListCategories())}
        rows: list[dict[str, str]] = []
        while len(rows) < MAX_INSIGHT_ROWS:
            filters = expenses.ExpenseFilters(
                start_date=start, end_date=end, limit=expenses.MAX_LIST_LIMIT, offset=len(rows)
            )
            page = self.bus.ask(expenses.ListExpenses(owner_id=owner_id, filters=filters)).items
            rows += [
                {
                    "spent_on": e.spent_on.isoformat(),
                    "amount": str(e.base_amount),
                    "category": names.get(e.category_id, categories.UNKNOWN_CATEGORY),
                    "merchant": e.merchant,
                    "payment_method": e.payment_method.value,
                }
                for e in page
                if e.base_amount is not None
            ]
            if len(page) < expenses.MAX_LIST_LIMIT:
                break
        return rows[:MAX_INSIGHT_ROWS]

    def answer(self, data: list[Any]) -> dict[str, Any] | None:
        """The insights, checked."""
        return _one(_Insights, data)


@dataclass(frozen=True)
class CurrencySkill:
    """currency / convert_currency: sends the request as a line of text, reads the conversion."""

    agent: str = "currency"
    skill_id: str = "convert_currency"
    artifact: str = "conversion"
    chip: str = ASK_CURRENCY

    def parts(self, request: DelegationRequest) -> list[Part]:
        """The request as one line ("4 USD to INR"): the agent reads it; no personal data goes with it."""
        return [TextPart(text=request.request)]

    def answer(self, data: list[Any]) -> dict[str, Any] | None:
        """The conversion, checked."""
        return _one(_Conversion, data)


def delegable_skills(bus: MessageBus) -> list[DelegatedSkill]:
    """Every skill the assistant may hand over (the receipt agent isn't one: it needs a file and has its own turn)."""
    return [InsightsSkill(bus=bus), CurrencySkill()]
