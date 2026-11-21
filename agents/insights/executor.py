"""The insights agent's AgentExecutor: a request becomes a task that may stop to ask which month, then is answered.

Application layer of the insights agent. The SDK's request handler (agent_kit/server.py) calls execute() for each
SendMessage, the first and any that resume the task:

    SUBMITTED -> INPUT_REQUIRED  no month, and the expenses span several: "Which month...?" (text, and the months as
                                 data); the client resumes the same task with the person's reply
              -> WORKING -> COMPLETED, with the `insights` artifact
                         -> FAILED     the model couldn't write the tips
              -> REJECTED            the request isn't one (wrong parts, malformed data)

A resumption's reply that names no month is asked about again. The original request is read back from the task's
history, which the kit's store keeps for an interrupted task (D205).
"""

import asyncio
import logging

from a2a.helpers import get_data_parts, get_text_parts, new_data_part, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Role, Task, TaskState
from a2a.utils.errors import TaskNotCancelableError
from pydantic import ValidationError

from agent_kit.tasks import fail, reject, start_task
from app.core.llm import LlmError
from app.core.months import YearMonth
from insights.analysis import analyse
from insights.contract import ARTIFACT_NAME, JSON_MEDIA_TYPE, InsightsRequest, MonthReply
from insights.months import month_in_reply, months_in
from insights.tips import TipWriter

logger = logging.getLogger(__name__)

# What the agent says (English: the client agent relays it in the person's language).
WHICH_MONTH = "Which month should I analyse? I have expenses for {months}."
NO_MONTH_IN_REPLY = "I didn't catch a month there. Which month should I analyse? I have expenses for {months}."
NO_EXPENSES = "There are no expenses to analyse."
# Why a task ends without an answer (for the client's log).
WRONG_PARTS = "expected one data part: an InsightsRequest"
WRONG_DATA = "the data part isn't an InsightsRequest"
WRONG_REPLY = "expected one part answering which month: a line of text or MonthReply data"
NOT_WRITTEN = "the tips couldn't be written"


class RejectedRequest(Exception):
    """A request the skill doesn't take; its message is the reason sent back."""


class InsightsExecutor(AgentExecutor):
    """Runs the analyze_spending skill, with the tip writer it's given."""

    def __init__(self, writer: TipWriter) -> None:
        """Keep the tip writer; it does the one model call per answered task."""
        self._writer = writer

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Answer the request (or its resumption): ask which month if it must, else publish the insights."""
        message, updater = await start_task(context, event_queue)
        resuming = context.current_task is not None and context.current_task.status.state == (
            TaskState.TASK_STATE_INPUT_REQUIRED
        )
        try:
            request = _original(context.current_task) if resuming else _request(message)
            reply = _reply(message, request) if resuming else None
        except RejectedRequest as exc:
            logger.info("task %s rejected: %s", updater.task_id, exc)
            await reject(updater, str(exc))
            return
        month = _month(request, reply)
        if month is None:
            await self._ask(updater, request, again=resuming)
            return
        await self._answer(updater, request, month)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Not supported: an analysis is one model call. Raises TaskNotCancelableError."""
        raise TaskNotCancelableError()

    async def _ask(self, updater: TaskUpdater, request: InsightsRequest, again: bool) -> None:
        """Stop INPUT_REQUIRED, asking which month, with the months there are as text and as data."""
        months = [str(month) for month in months_in(request.expenses)]
        question = (NO_MONTH_IN_REPLY if again else WHICH_MONTH).format(months=", ".join(months))
        parts = [new_text_part(question), new_data_part({"months": months}, media_type=JSON_MEDIA_TYPE)]
        logger.info("task %s asks which month (%d to choose from)", updater.task_id, len(months))
        await updater.requires_input(updater.new_agent_message(parts))

    async def _answer(self, updater: TaskUpdater, request: InsightsRequest, month: YearMonth) -> None:
        """Work out the month's figures, have the tips written, and publish them as the artifact."""
        await updater.start_work()
        figures = analyse(list(request.expenses), month, request.today)
        try:
            # The model port is synchronous: write in a worker thread, so the server keeps answering meanwhile.
            tips = await asyncio.to_thread(self._writer.tips, figures, request.question)
        except LlmError as exc:
            logger.warning("task %s failed: %s", updater.task_id, exc)
            await fail(updater, NOT_WRITTEN)
            return
        answer = figures.model_copy(update={"tips": tips})
        part = new_data_part(answer.model_dump(mode="json"), media_type=JSON_MEDIA_TYPE)
        await updater.add_artifact(parts=[part], name=ARTIFACT_NAME, last_chunk=True)
        await updater.complete()
        logger.info("task %s completed for %s", updater.task_id, month)


def _request(message: Message) -> InsightsRequest:
    """The first message's InsightsRequest. Raises RejectedRequest with the reason."""
    data = get_data_parts(message.parts)
    if len(message.parts) != 1 or len(data) != 1:
        raise RejectedRequest(WRONG_PARTS)
    try:
        request = InsightsRequest.model_validate(data[0])
    except ValidationError as exc:
        raise RejectedRequest(WRONG_DATA) from exc
    if not request.expenses:
        raise RejectedRequest(NO_EXPENSES)
    return request


def _original(task: Task | None) -> InsightsRequest:
    """The request a resumed task began with: its history's first message from the client."""
    first = next((sent for sent in (task.history if task else []) if sent.role == Role.ROLE_USER), None)
    if first is None:
        raise RejectedRequest(WRONG_PARTS)
    return _request(first)


def _reply(message: Message, request: InsightsRequest) -> YearMonth | None:
    """The month a resumption names (text or MonthReply data), or None if it names none."""
    texts, data = get_text_parts(message.parts), get_data_parts(message.parts)
    if len(message.parts) != 1:
        raise RejectedRequest(WRONG_REPLY)
    if data:
        try:
            return YearMonth.parse(MonthReply.model_validate(data[0]).month)
        except ValidationError as exc:
            raise RejectedRequest(WRONG_REPLY) from exc
    return month_in_reply(texts[0], request.today) if texts else None


def _month(request: InsightsRequest, reply: YearMonth | None) -> YearMonth | None:
    """The month to analyse: the request's, the reply's, or the only one the expenses cover; None if it must ask."""
    if request.month is not None:
        return YearMonth.parse(request.month)
    if reply is not None:
        return reply
    months = months_in(request.expenses)
    return months[0] if len(months) == 1 else None
