"""The assistant's expense-tools port: what the agent needs from the tools, whatever is behind them.

Port. The agent and the use cases (agent/agent.py, agent/tool_runs.py, agent/surfaces.py,
application/decisions.py, application/assistant.py) only know ExpenseTools, ToolOutput and
ToolsUnavailableError. The composition root (bootstrap.py) decides what's behind it, through module.py:
mcp_adapter.McpExpenseTools, which reaches this app's own MCP server in-process.

The tools always act for one person: the use cases bind them to the signed-in person (acting_for) before any call,
and an unbound adapter refuses to run a tool (D191).
"""

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import ExternalServiceError
from app.core.llm import ToolSpec


class ToolsUnavailableError(ExternalServiceError):
    """The expense tools couldn't be reached, or didn't answer in time."""


@dataclass(frozen=True)
class ToolOutput:
    """What one tool call returned: the text for the model, whether it worked, and the typed result."""

    text: str  # what the model reads: the result, or the error message
    ok: bool  # False: the tool ran and reported a problem (e.g. "Unknown category"), useful to the model
    data: dict[str, Any] | None = None  # the typed result (MCP structuredContent), for cards


class ExpenseTools(Protocol):
    """What the agent needs from the expense tools. Every method raises ToolsUnavailableError if unreachable."""

    def acting_for(self, owner_id: int) -> "ExpenseTools":
        """The same tools, acting for one person: every call reads and changes only `owner_id`'s expenses."""
        ...

    def specs(self) -> list[ToolSpec]:
        """Every tool, described for the model."""
        ...

    def call(self, name: str, arguments: dict[str, Any]) -> ToolOutput:
        """Run one tool for the person these tools act for. A tool that reports a problem returns ok=False rather
        than raising."""
        ...

    def changes_data(self, name: str) -> bool:
        """Whether a tool may change data, so the pages know to reload."""
        ...

    def category_names(self) -> list[str]:
        """The names of the expense categories, for the model's instructions and the form's choices."""
        ...
