"""The AG-UI adapter's output side: POST /agent's events, translated from the use cases' AgentEvents.

Adapter layer. routes.py's /agent route calls stream() with a run already checked by agui_request.read_request,
and sends each event it yields as one Server-Sent Event:

RUN_STARTED; then, as they happen, the reply's text as TEXT_MESSAGE_START / _CONTENT / _END, each tool
call as TOOL_CALL_START (with its chip labels) / _ARGS / _END / _RESULT (its outcome, not its text), a
STATE_SNAPSHOT after a tool changed data, and a CUSTOM "a2ui" event for each card or form; then RUN_FINISHED.
Once the stream has started, the HTTP status (200) has been sent and can't change, so a failure becomes a
RUN_ERROR event.

Everything a person reads here (chip labels, cards, a RUN_ERROR's message) is written in the request's language,
which routes.py passes in. Nothing else's words reach the browser: a tool's text and an outside service's error stay
on the server (D180).
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

from app.core.errors import AppError, ExternalServiceError
from app.core.i18n import Language, text
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
from app.modules.assistant.api.chip_labels import labels_for
from app.modules.assistant.api.protocol import STATE_DATA_VERSION, CustomEventName, MetadataKey
from app.modules.assistant.application.assistant import Assistant
from app.modules.assistant.i18n import ChatText

logger = logging.getLogger(__name__)

ASSISTANT_ROLE = "assistant"
# What TOOL_CALL_RESULT carries as the tool's content: nothing. The tool's text is written for the model (and, when
# the tool failed, it's the tool's error), so it stays on the server (D180); the chip shows the outcome
# (metadata.ok), and the reply explains it in the user's language.
NO_TOOL_CONTENT = ""


def _events_for(
    request: AgentRequest, owner_id: int, assistant: Assistant, today: date, language: Language
) -> Iterator[AgentEvent]:
    """Which use case this run is, for `owner_id` (the signed-in person): a decision on a delete card, a receipt to
    read, or a message (typed, or a form's Save)."""
    thread = request.thread_id
    if request.decision is not None:
        approved = request.decision.name == a2ui.ActionName.APPROVE_DELETE
        return assistant.decide(owner_id, thread, request.decision.surface_id, approved=approved, language=language)
    assert request.text is not None  # read_request sets exactly one of the two
    if request.receipt_id is not None:
        return assistant.read_receipt(owner_id, thread, request.receipt_id, request.text, today, language)
    # AG-UI clients name their threads themselves, so an id the person doesn't have yet starts a new conversation.
    return assistant.run_turn(owner_id, thread, request.text, today, language)


class _Writer:
    """Turns AgentEvents into AG-UI events, keeping track of the text message that's open.

    Also counts the data version: each tool that changed data raises it, and the client reloads its pages. Chip
    labels and cards are written in `language`.
    """

    def __init__(self, data_version: int, language: Language) -> None:
        """Start with no text message open, at the data version the client sent."""
        self.text_id: str | None = None  # the text message currently open, if any
        self.data_version = data_version
        self.language = language

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
                labels = labels_for(event.name, event.intent, self.language)
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
                card = a2ui.approval_card(approval_id, expense, self.language)
                yield CustomEvent(name=CustomEventName.A2UI, value=card.to_json())
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
        # That the tool has run. The event has no error field, so success goes in `metadata`.
        yield ToolCallResultEvent(
            message_id=uuid4().hex,
            tool_call_id=event.call_id,
            content=NO_TOOL_CONTENT,
            metadata={MetadataKey.OK: event.ok},
        )
        if event.changed_data:
            self.data_version += 1
            yield StateSnapshotEvent(snapshot={STATE_DATA_VERSION: self.data_version})
        # Only a tool that ran gets a card: an approval check's result must never look like a delete.
        if event.ok and event.intent == ToolIntent.RUN:
            card = a2ui.card_for(event.name, event.data, self.language)
            if card is not None:
                yield CustomEvent(name=CustomEventName.A2UI, value=card.to_json())


def _message_for_people(error: AppError, language: Language) -> str:
    """A RUN_ERROR's message: the error's text for people, or a generic one if it has none (D180).

    An error whose message is a plain string (an outside service's own words, e.g. Gemini's) isn't shown: the
    person is told the assistant's service failed, or that something went wrong. The words are in the log.
    """
    message = error.message_in(language)
    if message is not None:
        return message
    return text(language, ChatText.SERVICE_FAILED if isinstance(error, ExternalServiceError) else ChatText.RUN_FAILED)


def stream(
    request: AgentRequest, owner_id: int, assistant: Assistant, today: date, language: Language
) -> Iterator[BaseEvent]:
    """The whole AG-UI run for a checked request from `owner_id`: RUN_STARTED, the translated events, then
    RUN_FINISHED.

    A failed run doesn't raise: once streaming has begun, the status can't change, so it ends with a
    RUN_ERROR event instead (and the turn isn't saved). Its message is written in `language`.
    """
    yield RunStartedEvent(thread_id=request.thread_id, run_id=request.run_id)
    writer = _Writer(request.data_version, language)
    try:
        for event in _events_for(request, owner_id, assistant, today, language):
            yield from writer.write(event)
    # RUN_ERROR ends the run. The client keeps whatever text already arrived and shows the error. Its code is the
    # problem kind (AppError.slug, as in a problem's "type"), never a class name.
    except AppError as exc:
        # An expected problem; its words are logged, and the browser gets only a text written for people.
        logger.warning("agent run %s failed: %s", request.run_id, exc)
        yield RunErrorEvent(message=_message_for_people(exc, language), code=exc.slug)
        return
    except Exception:
        # A bug or a setup problem: the details go to the server log, not to the browser.
        logger.exception("agent run %s failed", request.run_id)
        yield RunErrorEvent(message=text(language, ChatText.RUN_FAILED), code=AppError.slug)
        return
    yield from writer.close_text()
    yield RunFinishedEvent(thread_id=request.thread_id, run_id=request.run_id)
