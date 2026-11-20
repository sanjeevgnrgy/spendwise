"""Remote agents, independent of the protocol: the RemoteAgents port (core layer: plain types and a Protocol, no I/O).

SpendWise's A2A agents (agents/: receipt, insights, currency) are separate services. What the app asks of them is
here: read what an agent offers (its card's skills), send it a message for one of its skills (a file, some data, some
text), or answer a task that stopped to ask something (resume it), and get back the task: its id, how it ended, its
data artifacts, and what the agent said. The composition root builds the adapter
(infrastructure/a2a/: the A2A SDK, each agent's card checked, D201) and passes it in; the modules' own adapters
(the assistant's receipt reader, the expenses module's exchange rates) use only this port, so no module imports an
agent SDK, and a check can pass a fake.

What an agent answers is outside data: callers validate it like any untrusted input before using it.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from app.core.errors import ExternalServiceError


class AgentUnavailableError(ExternalServiceError):
    """The agent couldn't be asked: not configured, unreachable, refused the key, not the agent expected, or timed
    out. Its message is for the log; callers raise their own catalogued error for people."""


# How a task ended, in this port's terms (A2A's terminal and interrupted states). OTHER covers anything else, which
# callers treat as "not done".
class TaskOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    INPUT_REQUIRED = "input_required"
    OTHER = "other"


@dataclass(frozen=True)
class FilePart:
    """A file sent to an agent: its bytes and media type."""

    data: bytes
    media_type: str


@dataclass(frozen=True)
class DataPart:
    """Structured data (JSON-serialisable) sent to an agent."""

    data: dict[str, Any]


@dataclass(frozen=True)
class TextPart:
    """Plain text sent to an agent."""

    text: str


Part = FilePart | DataPart | TextPart


@dataclass(frozen=True)
class SkillCard:
    """One skill an agent's card offers: which agent (by the app's name for it), the skill's id, and the card's own
    name, description and examples for it (the agent's words: outside data, for a model to choose by, D206)."""

    agent: str
    skill_id: str
    name: str
    description: str
    examples: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskRef:
    """A task to resume: its id and context id, as the agent gave them."""

    task_id: str
    context_id: str


@dataclass(frozen=True)
class AgentTask:
    """What a message became: the agent's task id and context id, how it ended, the data parts of the artifacts with
    the name asked for (in order), and the agent's own words on the task's status (a reason, or a question)."""

    task_id: str
    context_id: str
    outcome: TaskOutcome
    data: list[Any] = field(default_factory=list)
    message: str | None = None


class RemoteAgents(Protocol):
    """The app's remote agents, each known by its name (the key the composition root registered it under)."""

    def skills(self, agent: str) -> list[SkillCard]:
        """The skills `agent`'s card offers. Raises AgentUnavailableError if its card can't be read or isn't served
        at the agent's configured address."""
        ...

    def send(
        self, agent: str, skill: str, parts: Sequence[Part], artifact: str, resume: TaskRef | None = None
    ) -> AgentTask:
        """Send `parts` to `agent` for `skill` (as a new task, or answering the task `resume` names), wait for it to
        end or stop, and return it with the data of its artifacts named `artifact`. Raises AgentUnavailableError if
        the agent can't be asked (or doesn't offer `skill`)."""
        ...
