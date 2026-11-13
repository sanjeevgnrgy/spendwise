"""The assistant's use cases: answer a message, and carry out an Approve or Cancel.

They load a thread's history from the conversations module, run the agent, record approvals, and
save the turn once it has finished. Both routes (/chat and /agent) use them; neither knows about the
database or the tools.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from app.core.cqrs import MessageBus
from app.core.errors import NotFoundError
from app.core.llm import LanguageModel
from app.modules import conversations
from app.modules.assistant import agent
from app.modules.assistant.approvals import ExpenseSnapshot, RequestApproval, RestoreApproval, TakeApproval
from app.modules.assistant.events import AgentEvent, TurnFinished
from app.modules.assistant.tools import ExpenseTools
from app.modules.mcp import ExpenseView

logger = logging.getLogger(__name__)

# How many earlier turns (user message + everything up to the reply) are sent with each new
# message. Every one is paid for again on every step of the agent loop, so the cap trades memory
# for cost: enough for follow-ups like "make that 300", without resending a whole day's chat.
MAX_HISTORY_TURNS = 10
APPROVAL_PREFIX = "approval"


def new_thread_id() -> str:
    return uuid4().hex  # 32 characters: exactly the longest thread id allowed


@dataclass(frozen=True)
class Assistant:
    """The use cases, with what they need. Built once by the composition root."""

    bus: MessageBus
    tools: ExpenseTools
    llm: LanguageModel

    def _next_turn(self, thread_id: str) -> int:
        return (self.bus.ask(conversations.GetLastTurn(thread_id=thread_id)) or 0) + 1

    def _save(self, thread_id: str, turn: int, finished: TurnFinished) -> None:
        # Saved only when the turn completed, so a failed run leaves no half-turn behind.
        self.bus.execute(conversations.AppendTurn(thread_id=thread_id, turn=turn, messages=finished.messages))

    def _request_approval(self, thread_id: str, expense: ExpenseView) -> str:
        approval_id = f"{APPROVAL_PREFIX}_{uuid4().hex}"
        self.bus.execute(
            RequestApproval(thread_id=thread_id, approval_id=approval_id, expense=ExpenseSnapshot.of(expense))
        )
        return approval_id

    def run_turn(self, thread_id: str, text: str, today: date, rich_ui: bool = True) -> Iterator[AgentEvent]:
        """Answer one message in a thread (an unknown thread starts a new conversation)."""
        turn = self._next_turn(thread_id)
        # Only the last few turns are sent. Older ones stay stored, but the model no longer sees them.
        # Whole turns, so a tool call is never cut off from its result.
        history = self.bus.ask(conversations.GetHistory(thread_id=thread_id, from_turn=turn - MAX_HISTORY_TURNS))
        events = agent.run(
            text,
            today,
            history,
            self.llm,
            self.tools,
            rich_ui,
            request_approval=lambda expense: self._request_approval(thread_id, expense),
        )
        for event in events:
            if isinstance(event, TurnFinished):
                self._save(thread_id, turn, event)
            yield event

    def decide(self, thread_id: str, approval_id: str, approved: bool) -> Iterator[AgentEvent]:
        """Approve or Cancel on a delete card. WHAT gets deleted is the server's snapshot of that card.

        The whole decision (take the card, check, delete, save the turn) is carried out before the first
        event goes out. Nothing is left half done if the browser disconnects while reading, and on an error
        the card is put back at once, in this same thread.
        """
        card = self.bus.execute(TakeApproval(thread_id=thread_id, approval_id=approval_id))
        try:
            turn = self._next_turn(thread_id)
            events = list(agent.approval_turn(card.expense if card else None, approved, self.tools))
            finished = events[-1]
            assert isinstance(finished, TurnFinished)
            self._save(thread_id, turn, finished)
        except Exception:
            if card is not None:
                # The decision failed midway: put the card back as it was, so pressing Approve again works.
                # If the expense was deleted after all, Approve's check will find it gone.
                logger.warning("approval %s not completed; putting the card back", approval_id)
                self.bus.execute(RestoreApproval(thread_id=thread_id, approval_id=approval_id, card=card))
            raise
        yield from events

    def chat(self, message: str, thread_id: str | None, today: date) -> tuple[str, TurnFinished]:
        """POST /chat: the whole reply at once. Unlike AG-UI, the server names threads here."""
        if thread_id is None:
            thread_id = new_thread_id()
        elif self.bus.ask(conversations.GetLastTurn(thread_id=thread_id)) is None:
            # A typo'd id should be an error, not a silent new conversation.
            raise NotFoundError(f"Thread {thread_id} not found")
        finished = None
        for event in self.run_turn(thread_id, message, today, rich_ui=False):
            if isinstance(event, TurnFinished):
                finished = event
        if finished is None:  # can't happen: run_turn always ends with one
            raise RuntimeError("The agent ended without a result.")
        return thread_id, finished
