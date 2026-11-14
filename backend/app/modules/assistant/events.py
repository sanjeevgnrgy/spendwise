"""What happens during one turn of the agent, as plain events.

Shapes passed between layers. The agent (agent.py, surfaces.py, tool_runs.py), the Approve/Cancel decision
(decisions.py) and the use cases (turns.py) yield these. They say nothing about how a client sees them:
the AG-UI adapter (agui.py) turns them into AG-UI events for the browser, and POST /chat just waits
for the TurnFinished at the end.

A turn yields them as things happen: TextDelta pieces, a ToolStarted / ToolFinished pair per tool call,
an ApprovalRequested after a delete check, a FormRequested; then a TurnFinished, always last. A run that
fails raises instead, and has no TurnFinished. ToolCallSummary is also part of POST /chat's response
(schemas.ChatResponse).
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from app.core.llm import Message
from app.modules.assistant.a2ui import CreateSurfaceMessage, FormSource
from app.modules.mcp import ExpenseView


# Why a tool call is shown. agui.py picks the chip's labels by it, and draws a result card only for RUN:
# a delete check must never look like a delete.
class ToolIntent(StrEnum):
    RUN = "run"  # the tool runs as the model asked
    APPROVAL_CHECK = "approval_check"  # a delete: the expense is only looked up, and the user is asked


# A Pydantic model, not a dataclass, because POST /chat returns a list of them (its docstring is in the
# OpenAPI document). For a delete check in the web panel, `name` is delete_expense even though nothing
# was deleted.
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
    """A tool call is about to run. A ToolFinished with the same `call_id` follows it.

    `name` and `arguments` are the call as the model made it, or the server's own delete after an
    Approve. With intent APPROVAL_CHECK, it's the model's delete_expense, which only looks the expense up.
    """

    call_id: str
    name: str
    arguments: dict[str, Any]
    intent: ToolIntent = ToolIntent.RUN


@dataclass(frozen=True)
class ToolFinished:
    """A tool call has ended. `ok` is False if the tool reported an error or couldn't be reached.

    The AG-UI adapter turns it into the call's result, a "data changed" signal if `changed_data`, and a
    card if the tool has one.
    """

    call_id: str
    name: str
    ok: bool
    output: str  # what the tool returned, or its error message
    data: dict[str, Any] | None  # the typed result, for a card
    changed_data: bool  # it may have changed expenses: pages should reload
    intent: ToolIntent = ToolIntent.RUN


@dataclass(frozen=True)
class ApprovalRequested:
    """A delete waits for the user's Approve. `approval_id` names the server's record of it.

    It's also the approval card's surface id, so a click on the card names that record. `expense` is
    what the card shows; the record holds the same expense, version included.
    """

    approval_id: str
    expense: ExpenseView


@dataclass(frozen=True)
class FormRequested:
    """Show the user an expense form: the model's own if it passed the checks, else the built-in one (`source`)."""

    form: CreateSurfaceMessage
    source: FormSource


@dataclass(frozen=True)
class TurnFinished:
    """Always the last event: the whole reply, the tools used, and the messages to store.

    The use case (turns.py) saves `messages` as the thread's next turn when this arrives, so only a
    turn that finished is ever stored.
    """

    reply: str
    tool_calls: list[ToolCallSummary] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)


# Everything agent.Agent.run() and decisions.approval_turn() can yield.
AgentEvent = TextDelta | ToolStarted | ToolFinished | ApprovalRequested | FormRequested | TurnFinished
