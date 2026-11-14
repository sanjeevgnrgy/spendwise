"""The user's Approve or Cancel on a delete card, carried out without asking the model.

Application layer. turns.Assistant.decide takes the card's record (approvals.TakeApproval) and hands its
snapshot here; approval_turn yields the same kinds of events as the agent loop, ending with a TurnFinished
that the use case saves. No model is asked: the decision is the user's, and it costs no tokens.

Every outcome is stored as plain text ("I pressed Approve..." / "Done...") so later turns know what happened.
"""

import logging
from collections.abc import Generator, Iterator
from dataclasses import dataclass, field

from app.core.llm import AssistantText, UserText
from app.modules.assistant import a2ui
from app.modules.assistant.approvals import TTL_MINUTES, ExpenseSnapshot
from app.modules.assistant.events import AgentEvent, TextDelta, ToolCallSummary, TurnFinished
from app.modules.assistant.tool_runs import expense_in, look_up, run_and_report
from app.modules.assistant.tools import ExpenseTools
from app.modules.mcp import CONFIRM_ARGUMENT, EXPECTED_VERSION_ARGUMENT, EXPENSE_ID_ARGUMENT, ToolName

logger = logging.getLogger(__name__)

# What each click reads as in the stored conversation ("said"), and the reply. {ref} is the card's "#14".
STALE_SAID = "I pressed a button on an old delete card."
STALE_APPROVAL = (
    f"That card can't be used any more: it was already answered, or it's more than {TTL_MINUTES} minutes old. "
    "Ask me again if you still want to delete the expense."
)
CANCEL_SAID = "I pressed Cancel: don't delete expense {ref}."
CANCELLED = "Okay, I won't delete {ref}. Nothing was changed."
APPROVE_SAID = "I pressed Approve: delete expense {ref}."
CHANGED_SINCE = (
    "I couldn't confirm that expense {ref} is still what the card showed (it changed, it's gone, "
    "or the tools are unreachable), so I didn't delete it. Ask me again to see it as it is now."
)
DELETED = "Done: expense {ref} is deleted."
# {error} is the tool's own message, e.g. a version conflict or "unreachable".
DELETE_FAILED = "I couldn't delete {ref} just now ({error}). Nothing was deleted; ask me again in a moment."
# The id of the server's own delete call (not the model's), e.g. "approved_14".
APPROVED_CALL_PREFIX = "approved"


@dataclass(frozen=True)
class _Outcome:
    """How a decision ended: what the user's click reads as, the reply, and the tool the server ran (if any)."""

    said: str
    reply: str
    tool_calls: list[ToolCallSummary] = field(default_factory=list)


def approval_turn(expense: ExpenseSnapshot | None, approved: bool, tools: ExpenseTools) -> Iterator[AgentEvent]:
    """The user pressed Approve or Cancel on a delete card. No model is asked: the decision is theirs.

    `expense` is the server's snapshot of what that card showed, or None if the card was already
    answered, expired or belongs elsewhere. Yields the same kinds of events as agent.Agent.run, ending
    with a TurnFinished.
    """
    if expense is None:
        outcome = _stale()
    elif not approved:
        outcome = _cancelled(expense)
    else:
        outcome = yield from _approved(expense, tools)
    logger.info("approval decided: %s", "approved" if approved else "cancelled")
    yield TextDelta(outcome.reply)
    # Stored as plain text, so the conversation remembers what was decided and what happened.
    messages = [UserText(text=outcome.said), AssistantText(text=outcome.reply)]
    yield TurnFinished(reply=outcome.reply, tool_calls=outcome.tool_calls, messages=messages)


def _stale() -> _Outcome:
    """A click on a card that can't decide any more: nothing is checked or deleted."""
    return _Outcome(said=STALE_SAID, reply=STALE_APPROVAL)


def _cancelled(expense: ExpenseSnapshot) -> _Outcome:
    """Cancel: nothing is deleted, and the card is used up."""
    ref = a2ui.expense_ref(expense.id)
    return _Outcome(said=CANCEL_SAID.format(ref=ref), reply=CANCELLED.format(ref=ref))


def _approved(expense: ExpenseSnapshot, tools: ExpenseTools) -> Generator[AgentEvent, None, _Outcome]:
    """Approve: delete exactly what the card showed, if it's still that. Yields the delete as a tool call.

    The rule: Approve means "delete what the card showed". If that expense was edited since (or deleted, and
    the id reused), deleting it now would remove something the user never approved.
    """
    ref = a2ui.expense_ref(expense.id)
    said = APPROVE_SAID.format(ref=ref)
    # This check is for a clear answer; the guarantee is expected_version below, checked in the DELETE itself.
    if _current(tools, expense.id) != expense:
        return _Outcome(said=said, reply=CHANGED_SINCE.format(ref=ref))
    arguments = {EXPENSE_ID_ARGUMENT: expense.id, CONFIRM_ARGUMENT: True, EXPECTED_VERSION_ARGUMENT: expense.version}
    call_id = f"{APPROVED_CALL_PREFIX}_{expense.id}"
    output = yield from run_and_report(tools, call_id, ToolName.DELETE_EXPENSE, arguments)
    summary = ToolCallSummary(name=ToolName.DELETE_EXPENSE, arguments=arguments, ok=output.ok)
    reply = DELETED.format(ref=ref) if output.ok else DELETE_FAILED.format(ref=ref, error=output.text)
    return _Outcome(said=said, reply=reply, tool_calls=[summary])


def _current(tools: ExpenseTools, expense_id: int) -> ExpenseSnapshot | None:
    """The expense as it is now, or None if it's gone or the tools are unreachable."""
    expense = expense_in(look_up(tools, expense_id))
    return ExpenseSnapshot.of(expense) if expense is not None else None
