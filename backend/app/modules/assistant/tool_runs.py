"""Running one expense tool for the assistant: log it, call it, and report it as events.

Application layer, with no rules of its own about which tool runs when. Used by the agent loop (agent.py)
for the model's ordinary calls, by the web panel's delete check (surfaces.py) to look an expense up, and by
the Approve decision (decisions.py) for its check and its delete. Everything goes through the ExpenseTools
port (tools.py), so these work with any adapter behind it.
"""

import json
import logging
from collections.abc import Generator
from typing import Any

from pydantic import ValidationError

from app.modules.assistant.events import AgentEvent, ToolFinished, ToolStarted
from app.modules.assistant.tools import ExpenseTools, ToolOutput, ToolsUnavailableError
from app.modules.mcp import EXPENSE_ID_ARGUMENT, ExpenseFound, ExpenseView, ToolName

logger = logging.getLogger(__name__)

# How much of a tool's result goes into the DEBUG log line: enough to recognise it, not a whole list.
LOGGED_RESULT_LENGTH = 120
# What the model is told when the tools went away mid-turn, so it can tell the user instead of guessing.
UNREACHABLE = "The expense tools are unreachable right now."


def run_tool(tools: ExpenseTools, name: str, arguments: dict[str, Any]) -> ToolOutput:
    """Run one tool call and return its output. Never raises for unreachable tools.

    Problems go back to the model as a failed output (ok=False) instead of crashing the turn, so it can
    fix its call or explain what went wrong.
    """
    # Arguments are the user's data (amounts, merchants), so they're only logged at DEBUG.
    logger.info("  tool call: %s", name)
    logger.debug("    arguments: %s", json.dumps(arguments, default=str))
    try:
        output = tools.call(name, arguments)
    except ToolsUnavailableError as exc:
        # The tools went away mid-conversation. Tell the model, so it can tell the user.
        logger.warning("    -> tools unavailable: %s", exc)
        output = ToolOutput(text=UNREACHABLE, ok=False)
    logger.info("    -> %s", "ok" if output.ok else "error")
    logger.debug("    result: %s", output.text[:LOGGED_RESULT_LENGTH])
    return output


def run_and_report(
    tools: ExpenseTools, call_id: str, name: str, arguments: dict[str, Any]
) -> Generator[AgentEvent, None, ToolOutput]:
    """Run one tool, announcing it before (ToolStarted) and after (ToolFinished). Returns its output.

    Used as `output = yield from run_and_report(...)`, so the events reach the caller's caller. The
    ToolFinished says the data changed only if the tool worked and the server doesn't mark it read-only.
    """
    yield ToolStarted(call_id=call_id, name=name, arguments=arguments)
    output = run_tool(tools, name, arguments)
    changed = output.ok and tools.changes_data(name)
    yield ToolFinished(
        call_id=call_id, name=name, ok=output.ok, output=output.text, data=output.data, changed_data=changed
    )
    return output


def look_up(tools: ExpenseTools, expense_id: Any) -> ToolOutput:
    """Read one expense with the get_expense tool, without announcing it. Returns the tool's output.

    `expense_id` is passed on as given (the model's argument, unchecked): the tool validates it.
    """
    return run_tool(tools, ToolName.GET_EXPENSE, {EXPENSE_ID_ARGUMENT: expense_id})


def expense_in(output: ToolOutput) -> ExpenseView | None:
    """The expense in a successful get_expense output; None if the call failed or its result can't be read."""
    if not output.ok:
        return None
    try:
        return ExpenseFound.model_validate(output.data).expense
    except ValidationError:
        return None
