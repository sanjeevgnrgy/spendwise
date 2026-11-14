"""The AG-UI adapter's input side: POST /agent's RunAgentInput, checked and read into an AgentRequest.

Adapter layer. routes.py uses read_request as a FastAPI dependency, so a bad run is refused with an
ordinary 422 problem before anything is streamed; agui_stream.stream then gets the checked AgentRequest.
A run is either a decision on a delete card (Approve or Cancel, carried in forwardedProps) or a message for
the agent (typed, or a form's Save written out as one). A refused run's problem detail is written in the request's
language by web/problems.py: the errors here carry a translatable text, not words.
"""

from dataclasses import dataclass
from typing import Any

from ag_ui.core import RunAgentInput
from pydantic import TypeAdapter, ValidationError

from app.core.errors import BusinessRuleError
from app.core.i18n import translatable
from app.modules.assistant import a2ui
from app.modules.assistant.api.protocol import FORWARDED_A2UI_ACTION, STATE_DATA_VERSION
from app.modules.assistant.api.schemas import MAX_MESSAGE_LENGTH
from app.modules.assistant.i18n import ChatText
from app.modules.conversations import THREAD_ID_MAX_LENGTH, ThreadId

# AG-UI's names for a user's message and for a text part of one.
USER_ROLE = "user"
TEXT_PART = "text"
# The data version a run without a usable one starts from.
NO_DATA_VERSION = 0

_THREAD_ID = TypeAdapter(ThreadId)
# The clicks that decide a delete card, carried out without the model.
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
    else:
        text = _newest_user_text(run)
    return AgentRequest(thread_id, run.run_id, data_version, text=text)


def _newest_user_text(run: RunAgentInput) -> str:
    """The text of the newest user message, checked like POST /chat checks its `message`.

    Only that message is used, even if the client sends the whole conversation: the server keeps the
    thread's history itself, including the model's reasoning and tool results the browser never sees.
    Raises BusinessRuleError if there's no user message, or its text is empty or too long.
    """
    user_messages = [m for m in run.messages if m.role == USER_ROLE]
    if not user_messages:
        raise BusinessRuleError(translatable(ChatText.NO_USER_MESSAGE))
    content: Any = user_messages[-1].content
    # Content is either a string or a list of parts (text, images...). Only text is used.
    if not isinstance(content, str):
        content = "".join(part.text for part in content if part.type == TEXT_PART)
    text = content.strip()
    if not 1 <= len(text) <= MAX_MESSAGE_LENGTH:
        raise BusinessRuleError(translatable(ChatText.MESSAGE_LENGTH, max=MAX_MESSAGE_LENGTH))
    return text


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
