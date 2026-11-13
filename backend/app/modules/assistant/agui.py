"""The AG-UI adapter: POST /agent's run, in and out.

In: a RunAgentInput (the newest user message, or a button click carried in forwardedProps).
Out: AG-UI events, translated from the use cases' AgentEvents:

RUN_STARTED; then, as they happen, the reply's text as TEXT_MESSAGE_START / _CONTENT / _END, each tool
call as TOOL_CALL_START (with its chip labels) / _ARGS / _END / _RESULT, a STATE_SNAPSHOT after a tool
changed data, and a CUSTOM "a2ui" event for each card or form; then RUN_FINISHED. Once the stream has
started, the HTTP status (200) has been sent and can't change, so a failure becomes a RUN_ERROR event.
"""

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import uuid4

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    RunAgentInput,
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
from pydantic import TypeAdapter, ValidationError

from app.core.errors import AppError, BusinessRuleError
from app.modules.assistant import a2ui
from app.modules.assistant.events import (
    AgentEvent,
    ApprovalRequested,
    FormRequested,
    TextDelta,
    ToolFinished,
    ToolIntent,
    ToolStarted,
    TurnFinished,
)
from app.modules.assistant.protocol import (
    FORWARDED_A2UI_ACTION,
    STATE_DATA_VERSION,
    CustomEventName,
    MetadataKey,
    ToolLabels,
)
from app.modules.assistant.schemas import MAX_MESSAGE_LENGTH
from app.modules.assistant.turns import Assistant
from app.modules.conversations import THREAD_ID_MAX_LENGTH, ThreadId
from app.modules.mcp import ToolName

logger = logging.getLogger(__name__)

ASSISTANT_ROLE = "assistant"
USER_ROLE = "user"
TEXT_PART = "text"
INTERNAL_ERROR = "InternalError"

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
    ToolName.GET_EXPENSE: ToolLabels(running="Looking up the expense…", done="Found the expense", failed="Couldn't find the expense"),
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


def labels_for(name: str, intent: ToolIntent) -> ToolLabels:
    if intent == ToolIntent.APPROVAL_CHECK:
        return APPROVAL_CHECK_LABELS
    readable = name.replace("_", " ")
    return TOOL_LABELS.get(name, ToolLabels(running=f"Running {readable}…", done=f"Ran {readable}", failed=f"{readable} failed"))


# ---------- reading the run ----------


def _newest_user_text(run: RunAgentInput) -> str:
    """The text of the newest user message, checked like POST /chat checks its `message`.

    Only that message is used, even if the client sends the whole conversation: the server keeps the
    thread's history itself, including the model's reasoning and tool results the browser never sees.
    """
    user_messages = [m for m in run.messages if m.role == USER_ROLE]
    if not user_messages:
        raise BusinessRuleError("The run has no user message to answer.")
    content: Any = user_messages[-1].content
    # Content is either a string or a list of parts (text, images...). Only text is used.
    if not isinstance(content, str):
        content = "".join(part.text for part in content if part.type == TEXT_PART)
    text = content.strip()
    if not 1 <= len(text) <= MAX_MESSAGE_LENGTH:
        raise BusinessRuleError(f"The message must be 1 to {MAX_MESSAGE_LENGTH} characters long.")
    return text


def _button_click(run: RunAgentInput) -> a2ui.UserAction | None:
    """A button click (a form's Save, a card's Approve) sent with the run, if any. It's user input: checked."""
    props = run.forwarded_props
    if not isinstance(props, dict) or FORWARDED_A2UI_ACTION not in props:
        return None
    try:
        return a2ui.ActionMessage.model_validate(props[FORWARDED_A2UI_ACTION]).action
    except ValidationError as exc:
        raise BusinessRuleError("The button's action isn't valid.") from exc


def _data_version(state: Any) -> int:
    """dataVersion from the state the client sent with the run; 0 if it's missing or not a number."""
    value = state.get(STATE_DATA_VERSION) if isinstance(state, dict) else None
    return value if isinstance(value, int) else 0


_THREAD_ID = TypeAdapter(ThreadId)
_DECISIONS = (a2ui.ActionName.APPROVE_DELETE, a2ui.ActionName.CANCEL_DELETE)


@dataclass(frozen=True)
class AgentRequest:
    """A checked run: which thread, and either a decision on a delete card or a message for the agent."""

    thread_id: str
    run_id: str
    data_version: int
    text: str | None = None  # a typed message, or a form's values written out as one
    decision: a2ui.UserAction | None = None  # Approve or Cancel on a delete card


def read_request(run: RunAgentInput) -> AgentRequest:
    """Check a run before anything is streamed (a FastAPI dependency of POST /agent).

    Problems here are ordinary 422 problem responses: once the stream has started, the status is 200 and
    the only way left to say "no" is a RUN_ERROR event.
    """
    try:
        thread_id = _THREAD_ID.validate_python(run.thread_id)
    except ValidationError as exc:
        raise BusinessRuleError(f"threadId must be 1 to {THREAD_ID_MAX_LENGTH} characters long.") from exc
    data_version = _data_version(run.state)
    click = _button_click(run)
    if click is not None and click.name in _DECISIONS:
        # The user's decision, carried out without asking the model. The card's surface id names the
        # server's record of it; nothing else the browser sent is used.
        return AgentRequest(thread_id, run.run_id, data_version, decision=click)
    if click is not None:
        text = a2ui.describe_action(click)
        if len(text) > MAX_MESSAGE_LENGTH:
            raise BusinessRuleError(f"The form's values must be under {MAX_MESSAGE_LENGTH} characters in total.")
    else:
        text = _newest_user_text(run)
    return AgentRequest(thread_id, run.run_id, data_version, text=text)


def _events_for(request: AgentRequest, assistant: Assistant, today: date) -> Iterator[AgentEvent]:
    """Which use case this run is: a decision on a delete card, or a message (typed, or a form's Save)."""
    if request.decision is not None:
        approved = request.decision.name == a2ui.ActionName.APPROVE_DELETE
        return assistant.decide(request.thread_id, request.decision.surface_id, approved=approved)
    assert request.text is not None
    # AG-UI clients name their threads themselves, so an unknown id starts a new conversation.
    return assistant.run_turn(request.thread_id, request.text, today)


# ---------- writing events ----------


class _Writer:
    """Turns AgentEvents into AG-UI events, keeping track of the text message that's open."""

    def __init__(self, data_version: int) -> None:
        self.text_id: str | None = None  # the text message currently open, if any
        self.data_version = data_version

    def close_text(self) -> Iterator[BaseEvent]:
        if self.text_id is not None:
            yield TextMessageEndEvent(message_id=self.text_id)
            self.text_id = None

    def write(self, event: AgentEvent) -> Iterator[BaseEvent]:
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
                if event.ok and event.intent == ToolIntent.RUN:
                    card = a2ui.card_for(event.name, event.data)
                    if card is not None:
                        yield CustomEvent(name=CustomEventName.A2UI, value=card.to_json())
            case ApprovalRequested(approval_id=approval_id, expense=expense):
                yield CustomEvent(name=CustomEventName.A2UI, value=a2ui.approval_card(approval_id, expense).to_json())
            case FormRequested(form=form, source=source):
                # metadata.source says whose form this is: "model" (it passed the checks) or "fallback".
                yield CustomEvent(name=CustomEventName.A2UI, value=form.to_json(), metadata={MetadataKey.SOURCE: source})
            case TurnFinished():
                pass  # saved by the use case; the stream just ends


def stream(request: AgentRequest, assistant: Assistant, today: date) -> Iterator[BaseEvent]:
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
        yield RunErrorEvent(message="Something went wrong on the server. The server log has the details.", code=INTERNAL_ERROR)
        return
    yield from writer.close_text()
    yield RunFinishedEvent(thread_id=request.thread_id, run_id=request.run_id)
