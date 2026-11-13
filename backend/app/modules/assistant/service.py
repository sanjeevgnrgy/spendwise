import json
import logging
from collections.abc import Iterator
from datetime import date
from typing import Any
from uuid import uuid4

from ag_ui.core import (
    BaseEvent,
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
from sqlmodel import Session

from app.core import llm
from app.core.errors import BusinessRuleError, ExternalServiceError, NotFoundError

# Another module's public interface: the only way in to it.
from app.modules import categories
from app.modules.assistant import agent, parse, repository
from app.modules.assistant.models import ChatMessage
from app.modules.assistant.schemas import (
    MAX_MESSAGE_LENGTH,
    MAX_THREAD_ID_LENGTH,
    ChatResponse,
    ParseResponse,
    ThreadMessage,
    ThreadRead,
)

# How many earlier turns (user message + everything up to the reply) are sent with each new
# message. Every one is paid for again on every step of the agent loop, so the cap trades memory
# for cost: enough for follow-ups like "make that 300", without resending a whole day's chat.
MAX_HISTORY_TURNS = 10

logger = logging.getLogger("spendwise.assistant")


def answer(prompt: str) -> str:
    # Just a pass-through today. The orchestrator logic (tools, context, safety) grows
    # here in later phases, keeping the router free of business logic.
    return llm.ask_gemini(prompt)


def parse_expense_text(session: Session, text: str) -> ParseResponse:
    # The real category names, so Gemini can only pick one that exists.
    names = [c.name for c in categories.list_categories(session)]
    if not names:
        raise BusinessRuleError("There are no categories yet. Add some (or run backend/seed.py) first.")
    # The server's date, so "yesterday" means something. Per-user time zones can come with auth.
    parsed = parse.parse_expense(text, today=date.today(), category_names=names)
    return ParseResponse(expense=parsed, missing_fields=parse.missing_fields(parsed))


def _history(session: Session, thread_id: str, turn: int) -> list[dict[str, Any]]:
    # Only the last few turns are sent. Older ones stay stored (see GET /threads), but the
    # model no longer sees them. Whole turns, so a tool call is never cut off from its result.
    rows = repository.messages(session, thread_id, from_turn=turn - MAX_HISTORY_TURNS)
    return [row.content for row in rows]


def chat(session: Session, message: str, thread_id: str | None = None) -> ChatResponse:
    if thread_id is None:
        thread_id, turn, history = uuid4().hex, 1, []
    else:
        last = repository.last_turn(session, thread_id)
        if last is None:
            # A typo'd id should be an error, not a silent new conversation.
            raise NotFoundError(f"Thread {thread_id} not found")
        turn = last + 1
        history = _history(session, thread_id, turn)

    # The agent gets no database session: it reaches expense data only through the MCP server.
    result = agent.run(message, date.today(), history)
    repository.add_turn(session, thread_id, turn, result.steps)
    return ChatResponse(thread_id=thread_id, reply=result.reply, tool_calls=result.tool_calls)


def _newest_user_text(run: RunAgentInput) -> str:
    """The text of the newest user message, checked like POST /chat checks its `message`.

    Only that message is used, even if the client sends the whole conversation: the server keeps
    the thread's history itself, including Gemini's thoughts and tool results the browser never sees.
    """
    if not 1 <= len(run.thread_id) <= MAX_THREAD_ID_LENGTH:
        raise BusinessRuleError(f"threadId must be 1 to {MAX_THREAD_ID_LENGTH} characters long.")
    user_messages = [m for m in run.messages if m.role == "user"]
    if not user_messages:
        raise BusinessRuleError("The run has no user message to answer.")
    content = user_messages[-1].content
    # Content is either a string or a list of parts (text, images...). Only text is used.
    if not isinstance(content, str):
        content = "".join(part.text for part in content if part.type == "text")
    text = content.strip()
    if not 1 <= len(text) <= MAX_MESSAGE_LENGTH:
        raise BusinessRuleError(f"The message must be 1 to {MAX_MESSAGE_LENGTH} characters long.")
    return text


def _data_version(state: Any) -> int:
    """dataVersion from the state the client sent with the run; 0 if it's missing or not a number."""
    value = state.get("dataVersion") if isinstance(state, dict) else None
    return value if isinstance(value, int) else 0


def agent_run(session: Session, run: RunAgentInput) -> Iterator[BaseEvent]:
    """POST /agent: one AG-UI run, answering the newest user message as a stream of events.

    RUN_STARTED; then, as they happen, the reply's text as TEXT_MESSAGE_START / _CONTENT / _END, each
    tool call as TOOL_CALL_START / _ARGS / _END / _RESULT, and a STATE_SNAPSHOT after a tool changed
    data; then RUN_FINISHED. Once the stream has started, the HTTP status (200) has already been sent
    and can't change, so any failure is reported as a RUN_ERROR event instead.
    """
    yield RunStartedEvent(thread_id=run.thread_id, run_id=run.run_id)
    text_id: str | None = None  # the text message currently open, if any
    # AG-UI shared state: the client sends its dataVersion with the run and gets it back, raised,
    # after every tool that changed data. A new number is what makes the pages reload.
    data_version = _data_version(run.state)
    try:
        message = _newest_user_text(run)
        # AG-UI clients name their threads themselves, so an unknown id starts a new
        # conversation here (POST /chat answers 404 instead, because there the server names them).
        turn = (repository.last_turn(session, run.thread_id) or 0) + 1
        history = _history(session, run.thread_id, turn)

        for item in agent.stream(message, date.today(), history):
            if isinstance(item, str):
                if text_id is None:
                    text_id = uuid4().hex  # every piece names the message it belongs to
                    yield TextMessageStartEvent(message_id=text_id, role="assistant")
                yield TextMessageContentEvent(message_id=text_id, delta=item)

            elif isinstance(item, agent.ToolStarted):
                if text_id is not None:
                    # Close the text so far ("Let me check."); any text after the tool is a new message.
                    yield TextMessageEndEvent(message_id=text_id)
                    text_id = None
                # START, ARGS and END describe the call: END means "the arguments are complete", not
                # "the tool has run". The tool runs after these, while the panel shows "Saving expense…".
                yield ToolCallStartEvent(tool_call_id=item.call_id, tool_call_name=item.name)
                yield ToolCallArgsEvent(tool_call_id=item.call_id, delta=json.dumps(item.arguments))
                yield ToolCallEndEvent(tool_call_id=item.call_id)

            elif isinstance(item, agent.ToolFinished):
                # What the tool returned. The event has no error field, so success goes in `metadata`,
                # the slot every AG-UI event has for extra data.
                yield ToolCallResultEvent(
                    message_id=uuid4().hex, tool_call_id=item.call_id, content=item.text, metadata={"ok": item.ok}
                )
                if item.changed_data:
                    data_version += 1
                    yield StateSnapshotEvent(snapshot={"dataVersion": data_version})

            else:
                # The last item: the whole turn. Saved only when the run succeeds, like POST /chat.
                repository.add_turn(session, run.thread_id, turn, item.steps)
    # RUN_ERROR ends the run. The client keeps whatever text already arrived and shows the error.
    except (BusinessRuleError, ExternalServiceError) as exc:
        # Expected problems (e.g. Gemini's "high demand") carry a message meant for the user.
        logger.warning("agent run %s failed: %s", run.run_id, exc)
        yield RunErrorEvent(message=str(exc), code=type(exc).__name__)
        return
    except Exception:
        # A bug or a setup problem: the details go to the server log, not to the browser.
        logger.exception("agent run %s failed", run.run_id)
        yield RunErrorEvent(
            message="Something went wrong on the server. The server log has the details.", code="InternalError"
        )
        return

    if text_id is not None:
        yield TextMessageEndEvent(message_id=text_id)
    yield RunFinishedEvent(thread_id=run.thread_id, run_id=run.run_id)


def _readable_text(step: dict[str, Any]) -> str:
    if step["type"] == "function_call":
        return f"{step['name']}({json.dumps(step.get('arguments') or {})})"
    parts = step.get("result") if step["type"] == "function_result" else step.get("content")
    return "".join(part.get("text", "") for part in parts or [] if isinstance(part, dict))


def _to_thread_message(row: ChatMessage) -> ThreadMessage:
    return ThreadMessage(turn=row.turn, kind=row.kind, text=_readable_text(row.content), created_at=row.created_at)


def get_thread(session: Session, thread_id: str) -> ThreadRead:
    rows = repository.messages(session, thread_id)
    if not rows:
        raise NotFoundError(f"Thread {thread_id} not found")
    # Gemini's "thought" steps are stored (they're resent as history) but they're internal
    # reasoning, so they're left out of the readable conversation.
    shown = [_to_thread_message(row) for row in rows if row.kind != "thought"]
    return ThreadRead(thread_id=thread_id, messages=shown)
