"""Exchange rates from the currency agent: CurrencyAgentRates, the adapter behind ExchangeRates (port.py).

Adapter: the expenses module as the currency agent's client. It sends the agent named CURRENCY_AGENT a data part for
the convert_currency skill (agents/currency/contract.py: 1 unit of the currency, to the base currency, on a date)
through core/agents.RemoteAgents, and reads the finished task's conversion artifact, validated as outside data: the
currencies must be the ones asked about, the rate a positive decimal written as a string (a JSON number could be read
as a float), and the rate's date no later than the day asked for (D204). The composition root builds it, through
module.py, around the RemoteAgents it chose.
"""

import logging
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.agents import AgentUnavailableError, DataPart, RemoteAgents, TaskOutcome
from app.core.i18n import translatable
from app.core.money import BASE_CURRENCY
from app.modules.expenses.conversion.port import ExchangeRate, RatesUnavailableError, UnsupportedCurrencyError
from app.modules.expenses.i18n import ExpenseText

logger = logging.getLogger(__name__)

# The agent's name among the app's remote agents, the skill we call and the artifact it answers with.
CURRENCY_AGENT = "currency"
SKILL_ID = "convert_currency"
ARTIFACT_NAME = "conversion"
# What is asked for: the value of one unit, so the expense's own amount never leaves the app.
ONE_UNIT = "1"
# A decimal written as a string, as the agent's contract says rates are.
DECIMAL_TEXT = r"^\d{1,12}(\.\d{1,12})?$"


# The part of the agent's answer the app uses. Fields it doesn't know are ignored; these must be right.
class _Conversion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    from_currency: str
    to_currency: str
    rate: str = Field(pattern=DECIMAL_TEXT)
    rate_date: date


class CurrencyAgentRates:
    """ExchangeRates through the app's remote agents (`agents`): the currency agent answers, this checks it."""

    def __init__(self, agents: RemoteAgents) -> None:
        """Keep the remote agents; nothing is sent until a rate is needed."""
        self._agents = agents

    def to_base(self, currency: str, on: date) -> ExchangeRate:
        """The currency agent's rate from `currency` to INR on `on`. Raises UnsupportedCurrencyError if it refuses the
        currency, RatesUnavailableError if it can't be asked or its answer can't be used."""
        request = {"amount": ONE_UNIT, "from_currency": currency, "to_currency": BASE_CURRENCY, "on": on.isoformat()}
        try:
            task = self._agents.send(CURRENCY_AGENT, SKILL_ID, [DataPart(data=request)], ARTIFACT_NAME)
        except AgentUnavailableError as exc:
            raise RatesUnavailableError(translatable(ExpenseText.RATES_UNAVAILABLE, currency=currency)) from exc
        if task.outcome == TaskOutcome.REJECTED:
            # The agent won't convert it (it has no rate for this currency); its reason goes to the log.
            logger.info("currency task %s rejected %s: %s", task.task_id, currency, task.message)
            raise UnsupportedCurrencyError(translatable(ExpenseText.UNSUPPORTED_CURRENCY, currency=currency))
        try:
            if task.outcome != TaskOutcome.COMPLETED or len(task.data) != 1:
                raise ValueError(f"task {task.task_id} ended {task.outcome} with {len(task.data)} answers")
            answer = _Conversion.model_validate(task.data[0])
            if (answer.from_currency, answer.to_currency) != (currency, BASE_CURRENCY) or answer.rate_date > on:
                raise ValueError(f"task {task.task_id} answered for another conversion or a later day")
            rate = ExchangeRate(currency=currency, rate=Decimal(answer.rate), rate_date=answer.rate_date)
        except (ValueError, ValidationError) as exc:
            logger.warning("currency agent's answer unusable: %s", exc)
            raise RatesUnavailableError(translatable(ExpenseText.RATES_UNAVAILABLE, currency=currency)) from exc
        logger.info("rate %s->%s on %s: %s (task %s)", currency, BASE_CURRENCY, on, rate.rate, task.task_id)
        return rate
