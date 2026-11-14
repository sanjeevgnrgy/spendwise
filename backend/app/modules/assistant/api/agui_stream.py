"""The AG-UI adapter's output side: POST /agent's events, translated from the use cases' AgentEvents.

Adapter layer. routes.py's /agent route calls stream() with a run already checked by agui_request.read_request,
and sends each event it yields as one Server-Sent Event:

RUN_STARTED; then, as they happen, the reply's text as TEXT_MESSAGE_START / _CONTENT / _END, each tool
call as TOOL_CALL_START (with its chip labels) / _ARGS / _END / _RESULT, a STATE_SNAPSHOT after a tool
changed data, and a CUSTOM "a2ui" event for each card or form; then RUN_FINISHED. Once the stream has
started, the HTTP status (200) has been sent and can't change, so a failure becomes a RUN_ERROR event.
"""

import json
import logging
from collections.abc import Iterator
from datetime import date
from typing import assert_never
from uuid import uuid4

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)

from app.core.errors import AppError
from app.modules.assistant import a2ui
from app.modules.assistant.agent.events import (
    AgentEvent,
    ApprovalRequested,
    FormRequested,
    TextDelta,
    ToolFinished,
    ToolIntent,
    ToolStarted,
    TurnFinished,
)
from app.modules.assistant.api.agui_request import AgentRequest
from app.modules.assistant.api.protocol import STATE_DATA_VERSION, CustomEventName, MetadataKey, ToolLabels
from app.modules.assistant.application.assistant import Assistant
from app.modules.mcp import ToolName

logger = logging.getLogger(__name__)

ASSISTANT_ROLE = "assistant"
INTERNAL_ERROR = "InternalError"
# RUN_ERROR's message for an unexpected failure: the details stay in the server log, not in the browser.
RUN_FAILED = "Something went wrong on the server. The server log has the details."

# What each tool's status chip says. Here, next to the events that carry them, so the browser
# doesn't need to know any tool names.
TOOL_LABELS: dict[str, ToolLabels] = {
    ToolName.ADD_EXPENSE: ToolLabels(running="Saving expense…", done="Expense saved", failed="Couldn't save expense"),
    ToolName.UPDATE_EXPENSE: ToolLabels(
        running="Updating expense…", done="Expense updated", failed="Couldn't update expense"
    ),
    ToolName.DELETE_EXPENSE: ToolLabels(
        running="Deleting expense…", done="Expense deleted", failed="Couldn't delete expense"
    ),
    ToolName.GET_EXPENSE: ToolLabels(
        running="Looking up the expense…", done="Found the expense", failed="Couldn't find the expense"
    ),
    ToolName.LIST_EXPENSES: ToolLabels(
        running="Looking up expenses…", done="Looked up expenses", failed="Couldn't look up expenses"
    ),
    ToolName.GET_SUMMARY: ToolLabels(
        running="Adding up the month…", done="Added up the month", failed="Couldn't add up the month"
    ),
}
# A delete in the web panel only looks the expense up and asks: a chip must never claim a delete.
APPROVAL_CHECK_LABELS = ToolLabels(
    running="Checking the expense…", done="Waiting for your OK", failed="Couldn't find the expense"
)
# A tool without labels of its own: its name, made readable ("get_summary" -> "get summary").
DEFAULT_RUNNING = "Running {tool}…"
DEFAULT_DONE = "Ran {tool}"
DEFAULT_FAILED = "{tool} failed"


def labels_for(name: str, intent: ToolIntent) -> ToolLabels:
    """What the chip for a tool call says: an approval check's own labels, the tool's, or generic ones."""
    if intent == ToolIntent.APPROVAL_CHECK:
        return APPROVAL_CHECK_LABELS
    tool = name.replace("_", " ")
    default = ToolLabels(
        running=DEFAULT_RUNNING.format(tool=tool),
        done=DEFAULT_DONE.format(tool=tool),
        failed=DEFAULT_FAILED.format(tool=tool),
    )
    return TOOL_LABELS.get(name, default)


def _events_for(request: AgentRequest, assistant: Assistant, today: date) -> Iterator[AgentEvent]:
    """Which use case this run is: a decision on a delete card, or a message (typed, or a form's Save)."""
    if request.decision is not None:
        approved = request.decision.name == a2ui.ActionName.APPROVE_DELETE
        return assistant.decide(request.thread_id, request.decision.surface_id, approved=approved)
    assert request.text is not None  # read_request sets exactly one of the two
    # AG-UI clients name their threads themselves, so an unknown id starts a new conversation.
    return assistant.run_turn(request.thread_id, request.text, today)


class _Writer:
    """Turns AgentEvents into AG-UI events, keeping track of the text message that's open.

    Also counts the data version: each tool that changed data raises it, and the client reloads its pages.
    """

    def __init__(self, data_version: int) -> None:
        """Start with no text message open, at the data version the client sent."""
        self.text_id: str | None = None  # the text message currently open, if any
        self.data_version = data_version

    def close_text(self) -> Iterator[BaseEvent]:
        """End the open text message, if there is one, so the next text starts a new message."""
        if self.text_id is not None:
            yield TextMessageEndEvent(message_id=self.text_id)
            self.text_id = None

    def write(self, event: AgentEvent) -> Iterator[BaseEvent]:
        """The AG-UI events for one agent event (none for TurnFinished)."""
        match event:
            case TextDelta(text=text):
                if self.text_id is None:
                    self.text_id = uuid4().hex  # every piece names the message it belongs to
                    yield TextMessageStartEvent(message_id=self.text_id, role=ASSISTANT_ROLE)
                yield TextMessageContentEvent(message_id=self.text_id, delta=text)
            case ToolStarted():
                # Close the text so far ("Let me check."); any text after the tool is a new message.
                yield from self.close_text()
                # START, ARGS and END describe the call: END means "the arguments are complete", not "the
                # tool has run". The tool runs after these, while the panel shows "Saving expense…".
                labels = labels_for(event.name, event.intent)
                yield ToolCallStartEvent(
                    tool_call_id=event.call_id,
                    tool_call_name=event.name,
                    metadata={MetadataKey.LABELS: labels.model_dump()},
                )
                yield ToolCallArgsEvent(tool_call_id=event.call_id, delta=json.dumps(event.arguments))
                yield ToolCallEndEvent(tool_call_id=event.call_id)
            case ToolFinished():
                yield from self._tool_finished(event)
            case ApprovalRequested(approval_id=approval_id, expense=expense):
                yield CustomEvent(name=CustomEventName.A2UI, value=a2ui.approval_card(approval_id, expense).to_json())
            case FormRequested(form=form, source=source):
                # metadata.source says whose form this is: "model" (it passed the checks) or "fallback".
                yield CustomEvent(
                    name=CustomEventName.A2UI, value=form.to_json(), metadata={MetadataKey.SOURCE: source}
                )
            case TurnFinished():
                pass  # saved by the use case; the stream just ends
            case _:
                assert_never(event)

    def _tool_finished(self, event: ToolFinished) -> Iterator[BaseEvent]:
        """A tool's result; then a raised data version if it changed data, and its card if it has one."""
        # What the tool returned. The event has no error field, so success goes in `metadata`.
        yield ToolCallResultEvent(
            message_id=uuid4().hex,
            tool_call_id=event.call_id,
            content=event.output,
            metadata={MetadataKey.OK: event.ok},
        )
        if event.changed_data:
            self.data_version += 1
            yield StateSnapshotEvent(snapshot={STATE_DATA_VERSION: self.data_version})
        # Only a tool that ran gets a card: an approval check's result must never look like a delete.
        if event.ok and event.intent == ToolIntent.RUN:
            card = a2ui.card_for(event.name, event.data)
            if card is not None:
                yield CustomEvent(name=CustomEventName.A2UI, value=card.to_json())


def stream(request: AgentRequest, assistant: Assistant, today: date) -> Iterator[BaseEvent]:
    """The whole AG-UI run for a checked request: RUN_STARTED, the translated events, then RUN_FINISHED.

    A failed run doesn't raise: once streaming has begun, the status can't change, so it ends with a
    RUN_ERROR event instead (and the turn isn't saved).
    """
    yield RunStartedEvent(thread_id=request.thread_id, run_id=request.run_id)
    writer = _Writer(request.data_version)
    try:
        for event in _events_for(request, assistant, today):
            yield from writer.write(event)
    # RUN_ERROR ends the run. The client keeps whatever text already arrived and shows the error.
    except AppError as exc:
        # Expected problems (e.g. the model's "high demand") carry a message meant for the user.
        logger.warning("agent run %s failed: %s", request.run_id, exc)
        yield RunErrorEvent(message=str(exc), code=type(exc).__name__)
        return
    except Exception:
        # A bug or a setup problem: the details go to the server log, not to the browser.
        logger.exception("agent run %s failed", request.run_id)
        yield RunErrorEvent(message=RUN_FAILED, code=INTERNAL_ERROR)
        return
    yield from writer.close_text()
    yield RunFinishedEvent(thread_id=request.thread_id, run_id=request.run_id)
