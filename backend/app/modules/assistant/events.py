"""What happens during one turn of the agent, as plain events.

The agent and the use cases (turns.py) yield these. They say nothing about how a client sees them:
the AG-UI adapter (agui.py) turns them into AG-UI events for the browser, and POST /chat just waits
for the TurnFinished at the end.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from app.core.llm import Message
from app.modules.assistant.a2ui import CreateSurfaceMessage, FormSource
from app.modules.mcp import ExpenseView


class ToolIntent(StrEnum):
    RUN = "run"  # the tool runs as the model asked
    APPROVAL_CHECK = "approval_check"  # a delete: the expense is only looked up, and the user is asked


class ToolCallSummary(BaseModel):
    """One tool the agent ran while answering: what it called, with which arguments, and whether it worked."""

    name: str
    arguments: dict[str, Any]
    ok: bool


@dataclass(frozen=True)
class TextDelta:
    """A piece of the reply's text, as the model writes it."""

    text: str


@dataclass(frozen=True)
class ToolStarted:
    call_id: str
    name: str
    arguments: dict[str, Any]
    intent: ToolIntent = ToolIntent.RUN


@dataclass(frozen=True)
class ToolFinished:
    call_id: str
    name: str
    ok: bool
    output: str  # what the tool returned, or its error message
    data: dict[str, Any] | None  # the typed result, for a card
    changed_data: bool  # it may have changed expenses: pages should reload
    intent: ToolIntent = ToolIntent.RUN


@dataclass(frozen=True)
class ApprovalRequested:
    """A delete waits for the user's Approve. `approval_id` names the server's record of it."""

    approval_id: str
    expense: ExpenseView


@dataclass(frozen=True)
class FormRequested:
    form: CreateSurfaceMessage
    source: FormSource


@dataclass(frozen=True)
class TurnFinished:
    """Always the last event: the whole reply, the tools used, and the messages to store."""

    reply: str
    tool_calls: list[ToolCallSummary] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)


AgentEvent = TextDelta | ToolStarted | ToolFinished | ApprovalRequested | FormRequested | TurnFinished
