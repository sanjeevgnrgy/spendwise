"""The user's Approve or Cancel on a delete card, carried out without asking the model.

Application layer. Assistant.decide (assistant.py) takes the card's record (approvals.TakeApproval) and
hands its snapshot here; approval_turn yields the same kinds of events as the agent loop, ending with a
TurnFinished that the use case saves. No model is asked: the decision is the user's, and it costs no tokens.

Every outcome is stored as plain text ("I pressed Approve..." / "Done...") so later turns know what happened. The
reply is written in the request's language (the user reads it); what the click reads as ("said") stays English,
since only the model reads it, as the user's message in the conversation.
"""

import logging
from collections.abc import Generator, Iterator
from dataclasses import dataclass, field

from app.core import llm
from app.core.i18n import Language, text
from app.core.llm import UserText
from app.modules.assistant import a2ui
from app.modules.assistant.agent.events import AgentEvent, TextDelta, ToolCallSummary, TurnFinished
from app.modules.assistant.agent.tool_runs import expense_in, look_up, run_and_report
from app.modules.assistant.approvals import TTL_MINUTES, ExpenseSnapshot
from app.modules.assistant.i18n import ChatText
from app.modules.assistant.tools.port import ExpenseTools
from app.modules.mcp import CONFIRM_ARGUMENT, EXPECTED_VERSION_ARGUMENT, EXPENSE_ID_ARGUMENT, ToolName

logger = logging.getLogger(__name__)

# What each click reads as in the stored conversation ("said"), for the model. {ref} is the card's "#14". The
# replies are ChatText's (STALE_APPROVAL, CANCELLED, CHANGED_SINCE, DELETED, DELETE_FAILED).
STALE_SAID = "I pressed a button on an old delete card."
CANCEL_SAID = "I pressed Cancel: don't delete expense {ref}."
APPROVE_SAID = "I pressed Approve: delete expense {ref}."
# The id of the server's own delete call (not the model's), e.g. "approved_14".
APPROVED_CALL_PREFIX = "approved"


@dataclass(frozen=True)
class _Outcome:
    """How a decision ended: what the user's click reads as, the reply, and the tool the server ran (if any)."""

    said: str
    reply: str
    tool_calls: list[ToolCallSummary] = field(default_factory=list)


def approval_turn(
    expense: ExpenseSnapshot | None, approved: bool, tools: ExpenseTools, language: Language
) -> Iterator[AgentEvent]:
    """The user pressed Approve or Cancel on a delete card. No model is asked: the decision is theirs.

    `expense` is the server's snapshot of what that card showed, or None if the card was already
    answered, expired or belongs elsewhere. Yields the same kinds of events as agent.Agent.run, ending
    with a TurnFinished; the reply is in `language`.
    """
    if expense is None:
        outcome = _stale(language)
    elif not approved:
        outcome = _cancelled(expense, language)
    else:
        outcome = yield from _approved(expense, tools, language)
    logger.info("approval decided: %s", "approved" if approved else "cancelled")
    yield TextDelta(outcome.reply)
    # Stored as plain text, so the conversation remembers what was decided and what happened.
    messages = [UserText(text=outcome.said), llm.AssistantText(text=outcome.reply)]
    yield TurnFinished(reply=outcome.reply, tool_calls=outcome.tool_calls, messages=messages)


def _stale(language: Language) -> _Outcome:
    """A click on a card that can't decide any more: nothing is checked or deleted."""
    return _Outcome(said=STALE_SAID, reply=text(language, ChatText.STALE_APPROVAL, count=TTL_MINUTES))


def _cancelled(expense: ExpenseSnapshot, language: Language) -> _Outcome:
    """Cancel: nothing is deleted, and the card is used up."""
    ref = a2ui.expense_ref(expense.id)
    return _Outcome(said=CANCEL_SAID.format(ref=ref), reply=text(language, ChatText.CANCELLED, ref=ref))


def _approved(
    expense: ExpenseSnapshot, tools: ExpenseTools, language: Language
) -> Generator[AgentEvent, None, _Outcome]:
    """Approve: delete exactly what the card showed, if it's still that. Yields the delete as a tool call.

    The rule: Approve means "delete what the card showed". If that expense was edited since (or deleted, and
    the id reused), deleting it now would remove something the user never approved.
    """
    ref = a2ui.expense_ref(expense.id)
    said = APPROVE_SAID.format(ref=ref)
    # This check is for a clear answer; the guarantee is expected_version below, checked in the DELETE itself.
    if _current(tools, expense.id) != expense:
        return _Outcome(said=said, reply=text(language, ChatText.CHANGED_SINCE, ref=ref))
    arguments = {EXPENSE_ID_ARGUMENT: expense.id, CONFIRM_ARGUMENT: True, EXPECTED_VERSION_ARGUMENT: expense.version}
    call_id = f"{APPROVED_CALL_PREFIX}_{expense.id}"
    output = yield from run_and_report(tools, call_id, ToolName.DELETE_EXPENSE, arguments)
    summary = ToolCallSummary(name=ToolName.DELETE_EXPENSE, arguments=arguments, ok=output.ok)
    if output.ok:
        reply = text(language, ChatText.DELETED, ref=ref)
    else:
        # The tool's own message (English, from the MCP server), e.g. a version conflict or "unreachable".
        reply = text(language, ChatText.DELETE_FAILED, ref=ref, error=output.text)
    return _Outcome(said=said, reply=reply, tool_calls=[summary])


def _current(tools: ExpenseTools, expense_id: int) -> ExpenseSnapshot | None:
    """The expense as it is now, or None if it's gone or the tools are unreachable."""
    expense = expense_in(look_up(tools, expense_id))
    return ExpenseSnapshot.of(expense) if expense is not None else None
