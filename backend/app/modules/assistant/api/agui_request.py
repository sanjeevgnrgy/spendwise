"""The AG-UI adapter's input side: POST /agent's RunAgentInput, checked and read into an AgentRequest.

Adapter layer. routes.py uses read_request as a FastAPI dependency, so a bad run is refused with an
ordinary 422 problem before anything is streamed; agui_stream.stream then gets the checked AgentRequest.
A run is either a decision on a delete card (Approve or Cancel, carried in forwardedProps) or a message for
the agent (typed, or a form's Save written out as one), possibly with a receipt attached. A refused run's problem
detail is written in the request's language by web/problems.py: the errors here carry a translatable text, not words.
"""

from dataclasses import dataclass
from typing import Any

from ag_ui.core import RunAgentInput
from pydantic import TypeAdapter, ValidationError

from app.core.errors import BusinessRuleError
from app.core.i18n import translatable
from app.modules import receipts
from app.modules.assistant import a2ui
from app.modules.assistant.api.protocol import FORWARDED_A2UI_ACTION, RECEIPT_PROVIDER, STATE_DATA_VERSION
from app.modules.assistant.api.schemas import MAX_MESSAGE_LENGTH
from app.modules.assistant.i18n import ChatText
from app.modules.conversations import THREAD_ID_MAX_LENGTH, ThreadId

# AG-UI's names for a user's message, a text part of one, the parts that can carry a receipt, and the source that
# names a file the server already holds.
USER_ROLE = "user"
TEXT_PART = "text"
RECEIPT_PARTS = ("image", "document")
FILE_SOURCE = "file"
# The data version a run without a usable one starts from.
NO_DATA_VERSION = 0

_THREAD_ID = TypeAdapter(ThreadId)
_RECEIPT_ID = TypeAdapter(receipts.ReceiptId)
# The clicks that decide a delete card, carried out without the model.
_DECISIONS = (a2ui.ActionName.APPROVE_DELETE, a2ui.ActionName.CANCEL_DELETE)


@dataclass(frozen=True)
class AgentRequest:
    """A checked run: which thread, and either a decision on a delete card or a message for the agent."""

    thread_id: str
    run_id: str
    data_version: int
    text: str | None = None  # a typed message (may be "" with a receipt), or a form's values written out as one
    decision: a2ui.UserAction | None = None  # Approve or Cancel on a delete card
    receipt_id: int | None = None  # a receipt attached to the message: read it and offer it as the expense form


def read_request(run: RunAgentInput) -> AgentRequest:
    """Check a run before anything is streamed (a FastAPI dependency of POST /agent).

    Raises BusinessRuleError (a 422 problem) for a bad thread id, button click or message: once the stream
    has started, the status is 200 and the only way left to say "no" is a RUN_ERROR event.
    """
    try:
        thread_id = _THREAD_ID.validate_python(run.thread_id)
    except ValidationError as exc:
        raise BusinessRuleError(translatable(ChatText.THREAD_ID_LENGTH, max=THREAD_ID_MAX_LENGTH)) from exc
    data_version = _data_version(run.state)
    click = _button_click(run)
    if click is not None and click.name in _DECISIONS:
        # The user's decision, carried out without asking the model. The card's surface id names the
        # server's record of it; nothing else the browser sent is used.
        return AgentRequest(thread_id, run.run_id, data_version, decision=click)
    if click is not None:
        text = a2ui.describe_action(click)
        # Written out, the form's values become a message, so they must fit in one like a typed message.
        if len(text) > MAX_MESSAGE_LENGTH:
            raise BusinessRuleError(translatable(ChatText.FORM_TOO_LONG, max=MAX_MESSAGE_LENGTH))
        return AgentRequest(thread_id, run.run_id, data_version, text=text)
    text, receipt_id = _newest_user_message(run)
    return AgentRequest(thread_id, run.run_id, data_version, text=text, receipt_id=receipt_id)


def _newest_user_message(run: RunAgentInput) -> tuple[str, int | None]:
    """The newest user message: its text, checked like POST /chat checks its `message`, and its receipt, if any.

    Only that message is used, even if the client sends the whole conversation: the server keeps the
    thread's history itself, including the model's reasoning and tool results the browser never sees.
    A message with a receipt may have no text. Raises BusinessRuleError if there's no user message, its text is
    empty (without a receipt) or too long, or its attachment isn't one receipt uploaded here.
    """
    user_messages = [m for m in run.messages if m.role == USER_ROLE]
    if not user_messages:
        raise BusinessRuleError(translatable(ChatText.NO_USER_MESSAGE))
    content: Any = user_messages[-1].content
    # Content is either a string or a list of parts (text, images, documents...).
    parts = [] if isinstance(content, str) else list(content)
    if parts:
        content = "".join(part.text for part in parts if part.type == TEXT_PART)
    receipt_id = _receipt_in([part for part in parts if part.type != TEXT_PART])
    text = content.strip()
    shortest = 0 if receipt_id is not None else 1
    if not shortest <= len(text) <= MAX_MESSAGE_LENGTH:
        raise BusinessRuleError(translatable(ChatText.MESSAGE_LENGTH, max=MAX_MESSAGE_LENGTH))
    return text, receipt_id


def _receipt_in(media: list[Any]) -> int | None:
    """The receipt id a message's non-text parts point at, or None if there are none.

    It's user input, so it's checked: exactly one image or document part, whose source is a file handle this app
    issued (RECEIPT_PROVIDER) naming a receipt id. Anything else (several files, bytes sent inline or by URL rather
    than uploaded first, audio, another provider's handle, a malformed id) raises BusinessRuleError.
    """
    if not media:
        return None
    if len(media) > 1:
        raise BusinessRuleError(translatable(ChatText.ONE_RECEIPT))
    source = getattr(media[0], "source", None)
    if (
        media[0].type not in RECEIPT_PARTS
        or getattr(source, "type", None) != FILE_SOURCE
        or getattr(source, "provider", None) != RECEIPT_PROVIDER
    ):
        raise BusinessRuleError(translatable(ChatText.INVALID_ATTACHMENT))
    try:
        return _RECEIPT_ID.validate_python(source.value)
    except ValidationError as exc:
        raise BusinessRuleError(translatable(ChatText.INVALID_ATTACHMENT)) from exc


def _button_click(run: RunAgentInput) -> a2ui.UserAction | None:
    """A button click (a form's Save, a card's Approve) sent with the run, or None if there's none.

    It's user input, so it's checked: raises BusinessRuleError if it isn't a valid A2UI action.
    """
    props = run.forwarded_props
    if not isinstance(props, dict) or FORWARDED_A2UI_ACTION not in props:
        return None
    try:
        return a2ui.ActionMessage.model_validate(props[FORWARDED_A2UI_ACTION]).action
    except ValidationError as exc:
        raise BusinessRuleError(translatable(ChatText.INVALID_ACTION)) from exc


def _data_version(state: Any) -> int:
    """dataVersion from the state the client sent with the run; NO_DATA_VERSION if missing or not a number."""
    value = state.get(STATE_DATA_VERSION) if isinstance(state, dict) else None
    return value if isinstance(value, int) else NO_DATA_VERSION
