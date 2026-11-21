"""The currency agent's AgentExecutor: one request becomes one task, converted at once, answered with a data artifact.

Application layer of the currency agent. The SDK's request handler (agent_kit/server.py) calls execute() for each
SendMessage; it reads the message's one part (a ConversionRequest as data, or one line of text), asks the
RateProvider and publishes the task's states:

    SUBMITTED -> COMPLETED, with the `conversion` artifact
              -> REJECTED   the request isn't one (wrong parts, unreadable), or a currency has no rate

No model is involved: the arithmetic is core.money's convert_minor, the one rule the backend uses too (D203).
"""

import logging
from decimal import Decimal

from a2a.helpers import get_data_parts, get_text_parts, new_data_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message
from a2a.utils.errors import TaskNotCancelableError
from pydantic import ValidationError

from agent_kit.tasks import reject, start_task
from app.core.clock import Clock
from app.core.money import convert_minor, paise_to_rupees, rupees_to_paise
from currency.contract import ARTIFACT_NAME, JSON_MEDIA_TYPE, ConversionAnswer, ConversionRequest, parse_text
from currency.rates import RateProvider, UnsupportedCurrencyError

logger = logging.getLogger(__name__)

# Why a task ends without an answer (English, for the client's log; never shown to a person).
WRONG_PARTS = "expected exactly one part: a ConversionRequest as data, or one line such as '4 USD to INR'"
WRONG_DATA = "the data part isn't a ConversionRequest"
WRONG_TEXT = "the text isn't a conversion, e.g. '4 USD to INR' or '4.50 EUR in INR on 2026-11-19'"
UNSUPPORTED = "unsupported currency: {currency}"


class RejectedRequest(Exception):
    """A request the skill doesn't take; its message is the reason sent back (one of the texts above)."""


class CurrencyExecutor(AgentExecutor):
    """Runs the convert_currency skill with the rates and the clock it's given."""

    def __init__(self, rates: RateProvider, clock: Clock) -> None:
        """Keep the rate provider (the mock, for now) and the clock (for "today" when no date is given)."""
        self._rates = rates
        self._clock = clock

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Convert the request's amount and publish the task's states and its artifact. Raises nothing for a bad
        request or a currency without a rate: they end the task REJECTED, with a reason."""
        message, updater = await start_task(context, event_queue)
        try:
            request = _request_of(message)
            answer = self._convert(request)
        except RejectedRequest as exc:
            logger.info("task %s rejected: %s", updater.task_id, exc)
            await reject(updater, str(exc))
            return
        part = new_data_part(answer.model_dump(mode="json"), media_type=JSON_MEDIA_TYPE)
        await updater.add_artifact(parts=[part], name=ARTIFACT_NAME, last_chunk=True)
        await updater.complete()
        logger.info(
            "task %s: %s %s -> %s %s",
            updater.task_id,
            answer.amount,
            answer.from_currency,
            answer.converted,
            answer.to_currency,
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported: a conversion ends as soon as it starts. Raises TaskNotCancelableError."""
        raise TaskNotCancelableError()

    def _convert(self, request: ConversionRequest) -> ConversionAnswer:
        """The answer for `request`, at the provider's rate for its day (today if none, or if it's in the future).
        Raises RejectedRequest for a currency the provider has no rate for."""
        today = self._clock.today()
        on = min(request.on or today, today)
        try:
            rate = self._rates.rate(request.from_currency, request.to_currency, on)
        except UnsupportedCurrencyError as exc:
            raise RejectedRequest(UNSUPPORTED.format(currency=exc)) from exc
        converted = convert_minor(rupees_to_paise(request.amount), rate.value)
        return ConversionAnswer(
            amount=request.amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            rate=_plain(rate.value),
            rate_date=rate.as_of,
            # Money keeps its two decimals ("338.00"); only the rate is written without trailing zeros.
            converted=str(paise_to_rupees(converted)),
            source=rate.source,
        )


def _request_of(message: Message) -> ConversionRequest:
    """The message's request: its one data part, or its one line of text. Raises RejectedRequest with the reason."""
    if len(message.parts) != 1:
        raise RejectedRequest(WRONG_PARTS)
    data, texts = get_data_parts(message.parts), get_text_parts(message.parts)
    if data:
        try:
            return ConversionRequest.model_validate(data[0])
        except ValidationError as exc:
            raise RejectedRequest(WRONG_DATA) from exc
    request = parse_text(texts[0]) if texts else None
    if request is None:
        raise RejectedRequest(WRONG_TEXT if texts else WRONG_PARTS)
    return request


def _plain(value: Decimal) -> str:
    """A decimal as plain digits, without trailing zeros or an exponent: 84.5000000000 -> "84.5", 1E+2 -> "100"."""
    return format(value.normalize(), "f")
