"""Where the user talks to the assistant, and what that changes: text chat (POST /chat) or the web panel.

Application layer. A Surface decides the three things that differ between the two (everything else in the
agent loop is the same):
- the rules in the system instruction (prompts.PromptRules);
- the tools the model is shown (their specs);
- which tool calls it handles itself instead of running them as asked (call handlers).

TextChat shows only text: details and delete confirmations go by words. WebPanel can show forms, cards and
Approve buttons, so there a delete is never run: the expense is looked up and the user is asked
(human in the loop). turns.py picks the surface per use case; agent.py only talks to the protocol.
"""

from collections.abc import Callable, Generator, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Protocol

from app.core.llm import ToolCall, ToolResult, ToolSpec
from app.modules.assistant import a2ui
from app.modules.assistant.events import (
    AgentEvent,
    ApprovalRequested,
    ToolCallSummary,
    ToolFinished,
    ToolIntent,
    ToolStarted,
)
from app.modules.assistant.prompts import (
    ASK_FOR_MISSING,
    CARDS_SHOW_DETAILS,
    CONFIRM_DELETE_IN_WORDS,
    DELETE_IN_WEB_PANEL,
    DELETE_NEEDS_APPROVAL,
    NO_CARDS,
    PromptRules,
)
from app.modules.assistant.tool_runs import expense_in, look_up
from app.modules.assistant.tools import ExpenseTools, ToolOutput
from app.modules.mcp import EXPENSE_ID_ARGUMENT, ExpenseView, ToolName

# Added to a delete check's result for the model, so it doesn't think the delete simply failed and retry it.
AWAITING_APPROVAL = (
    "\n(Nothing was deleted. The user now sees this expense with Approve and Cancel buttons; only their "
    "Approve deletes it.)"
)
# The model's result when the looked-up expense isn't in the expected shape: no card can be shown for it.
UNREADABLE_EXPENSE = "The expense couldn't be read, so it can't be deleted here."

# Records a delete card for the expense shown and returns the card's id (turns.Assistant provides it).
RequestApprovalFn = Callable[[ExpenseView], str]


@dataclass(frozen=True)
class CallOutcome:
    """How one tool call ended, for the agent loop.

    `result` goes back to the model; `summary` is listed in the reply's tool calls (None: not a tool the
    agent ran, e.g. a form put on screen); `ends_turn` stops the turn after this step's calls.
    """

    result: ToolResult
    summary: ToolCallSummary | None
    ends_turn: bool

    @classmethod
    def reported(cls, call: ToolCall, output: ToolOutput) -> "CallOutcome":
        """The outcome of a call that ran (or was checked): its output for the model, and its summary."""
        return cls(
            result=ToolResult(call_id=call.call_id, name=call.name, output=output.text, is_error=not output.ok),
            summary=ToolCallSummary(name=call.name, arguments=call.arguments, ok=output.ok),
            ends_turn=False,
        )


# Handles one tool call in place of running it as asked: yields events, returns how it ended.
CallHandler = Callable[[ToolCall], Generator[AgentEvent, None, CallOutcome]]


class Surface(Protocol):
    """What differs between text chat and the web panel. agent.Agent.run takes one per turn."""

    def prompt_rules(self, category_names: list[str]) -> PromptRules:
        """The surface's rules for the system instruction (forms, deleting, cards)."""
        ...

    def tool_specs(self, specs: list[ToolSpec]) -> list[ToolSpec]:
        """The tools as the model sees them here, given every tool the server offers. In order."""
        ...

    def call_handlers(self, tools: ExpenseTools) -> Mapping[str, CallHandler]:
        """Tool name -> its handler, for calls this surface handles itself. Others run as asked."""
        ...


class TextChat:
    """POST /chat: replies are text only, so no forms, no cards and no buttons."""

    def prompt_rules(self, category_names: list[str]) -> PromptRules:
        """Ask for missing details in words, and delete only after the user confirms in words."""
        return PromptRules(missing=ASK_FOR_MISSING, deleting=CONFIRM_DELETE_IN_WORDS, cards=NO_CARDS)

    def tool_specs(self, specs: list[ToolSpec]) -> list[ToolSpec]:
        """Every tool, exactly as the server describes it (the show-form tool isn't offered here)."""
        return specs

    def call_handlers(self, tools: ExpenseTools) -> Mapping[str, CallHandler]:
        """None: every call runs as the model asked (a delete needs confirmed=true, see the rules)."""
        return {}


@dataclass(frozen=True)
class WebPanel:
    """The web app's chat panel (POST /agent): forms, cards, and Approve/Cancel for every delete.

    `request_approval` records a delete card for the expense shown and returns its id; the card's Approve
    is carried out later by decisions.approval_turn, never by the model.
    """

    request_approval: RequestApprovalFn

    def prompt_rules(self, category_names: list[str]) -> PromptRules:
        """The form rules (with the category options), the approval rule for deletes, and the card rule."""
        return PromptRules(
            missing=a2ui.form_instructions(category_names), deleting=DELETE_NEEDS_APPROVAL, cards=CARDS_SHOW_DETAILS
        )

    def tool_specs(self, specs: list[ToolSpec]) -> list[ToolSpec]:
        """The server's tools, with delete reduced to asking, then the show-form tool (always last)."""
        shown = [_ask_only(spec) if spec.name == ToolName.DELETE_EXPENSE else spec for spec in specs]
        return [*shown, a2ui.SHOW_FORM_TOOL]

    def call_handlers(self, tools: ExpenseTools) -> Mapping[str, CallHandler]:
        """delete_expense becomes an approval check: whatever the model asked, nothing is deleted here."""
        return {ToolName.DELETE_EXPENSE: partial(self._approval_check, tools)}

    def _approval_check(self, tools: ExpenseTools, call: ToolCall) -> Generator[AgentEvent, None, CallOutcome]:
        """A delete in the web panel: look the expense up, and ask the user. Nothing is deleted here.

        Yields the check as a tool call (intent APPROVAL_CHECK, so no chip or card claims a delete), then an
        ApprovalRequested with the card's id. The model is told the user now decides.
        """
        intent = ToolIntent.APPROVAL_CHECK
        yield ToolStarted(call_id=call.call_id, name=call.name, arguments=call.arguments, intent=intent)
        output = look_up(tools, call.arguments.get(EXPENSE_ID_ARGUMENT))
        yield ToolFinished(
            call_id=call.call_id,
            name=call.name,
            ok=output.ok,
            output=output.text,
            data=output.data,
            changed_data=False,  # only looked up: the pages needn't reload
            intent=intent,
        )
        if not output.ok:
            return CallOutcome.reported(call, output)
        expense = expense_in(output)
        if expense is None:
            return CallOutcome.reported(call, ToolOutput(text=UNREADABLE_EXPENSE, ok=False))
        yield ApprovalRequested(approval_id=self.request_approval(expense), expense=expense)
        return CallOutcome.reported(call, ToolOutput(text=output.text + AWAITING_APPROVAL, ok=True, data=output.data))


def _ask_only(spec: ToolSpec) -> ToolSpec:
    """delete_expense as the web panel shows it: described as a request, with only the expense's id.

    There, a delete only asks the user (Approve/Cancel), so the model has nothing to confirm, and isn't
    even offered a way to delete by itself.
    """
    parameters = spec.parameters
    return spec.model_copy(
        update={
            "description": DELETE_IN_WEB_PANEL,
            # Only which expense: the interlock and the version are the server's business here.
            "parameters": {
                **parameters,
                "properties": {k: v for k, v in parameters.get("properties", {}).items() if k == EXPENSE_ID_ARGUMENT},
                "required": [r for r in parameters.get("required", []) if r == EXPENSE_ID_ARGUMENT],
            },
        }
    )
