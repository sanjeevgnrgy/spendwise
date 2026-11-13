import json
from datetime import date
from typing import Any
from uuid import uuid4

from sqlmodel import Session

from app.core import llm
from app.core.errors import BusinessRuleError, NotFoundError

# Another module's public interface: the only way in to it.
from app.modules import categories
from app.modules.assistant import agent, parse, repository
from app.modules.assistant.models import ChatMessage
from app.modules.assistant.schemas import ChatResponse, ParseResponse, ThreadMessage, ThreadRead

# How many earlier turns (user message + everything up to the reply) are sent with each new
# message. Every one is paid for again on every step of the agent loop, so the cap trades memory
# for cost: enough for follow-ups like "make that 300", without resending a whole day's chat.
MAX_HISTORY_TURNS = 10


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


def chat(session: Session, message: str, thread_id: str | None = None) -> ChatResponse:
    if thread_id is None:
        thread_id, turn, history = uuid4().hex, 1, []
    else:
        last = repository.last_turn(session, thread_id)
        if last is None:
            # A typo'd id should be an error, not a silent new conversation.
            raise NotFoundError(f"Thread {thread_id} not found")
        turn = last + 1
        # Only the last few turns are sent. Older ones stay stored (see GET /threads), but the
        # model no longer sees them. Whole turns, so a tool call is never cut off from its result.
        rows = repository.messages(session, thread_id, from_turn=turn - MAX_HISTORY_TURNS)
        history = [row.content for row in rows]

    # The agent gets no database session: it reaches expense data only through the MCP server.
    result = agent.run(message, date.today(), history)
    repository.add_turn(session, thread_id, turn, result.steps)
    return ChatResponse(thread_id=thread_id, reply=result.reply, tool_calls=result.tool_calls)


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
