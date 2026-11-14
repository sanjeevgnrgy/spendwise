"""The assistant's use cases: answer a message, and carry out an Approve or Cancel.

Application layer. They load a thread's history from the conversations module, run the agent (agent.py)
on the right surface (surfaces.py), record approvals, and save the turn once it has finished. Both routes
(/chat and /agent) use them; neither knows about the database or the tools.

Everything goes through the bus in short, separate steps (read the history, record a card, save the
turn), never one transaction around the whole run: a model call can take a minute or two, and no
database session stays open while it does.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from app.core.cqrs import MessageBus
from app.core.errors import NotFoundError
from app.core.llm import ToolCallingModel
from app.modules import conversations
from app.modules.assistant.agent import Agent
from app.modules.assistant.approvals import ExpenseSnapshot, RequestApproval, RestoreApproval, TakeApproval
from app.modules.assistant.decisions import approval_turn
from app.modules.assistant.events import AgentEvent, TurnFinished
from app.modules.assistant.surfaces import Surface, TextChat, WebPanel
from app.modules.assistant.tools import ExpenseTools
from app.modules.mcp import ExpenseView

logger = logging.getLogger(__name__)

# How many earlier turns (user message + everything up to the reply) are sent with each new
# message. Every one is paid for again on every step of the agent loop, so the cap trades memory
# for cost: enough for follow-ups like "make that 300", without resending a whole day's chat.
MAX_HISTORY_TURNS = 10
# Starts every approval id (and so every approval card's surface id), e.g. "approval_3f2a...".
APPROVAL_PREFIX = "approval"
# Said by POST /chat if the agent ever ended without a TurnFinished (it always ends with one).
NO_RESULT = "The agent ended without a result."


def new_thread_id() -> str:
    """A fresh, random thread id, for POST /chat when the client doesn't send one."""
    return uuid4().hex  # 32 characters: exactly the longest thread id allowed


@dataclass(frozen=True)
class Assistant:
    """The use cases, with what they need. Built once by the composition root.

    module.create_router builds it from the bus, the tools adapter and the language model, and api.py's
    routes call it: run_turn and decide through agui.py for POST /agent, chat for POST /chat.
    """

    bus: MessageBus
    tools: ExpenseTools
    llm: ToolCallingModel

    def _next_turn(self, thread_id: str) -> int:
        """The number the thread's next turn gets: 1 for a new thread."""
        return (self.bus.ask(conversations.GetLastTurn(thread_id=thread_id)) or 0) + 1

    def _save(self, thread_id: str, turn: int, finished: TurnFinished) -> None:
        """Store a finished turn's messages as turn number `turn` of the thread, in one transaction."""
        # Saved only when the turn completed, so a failed run leaves no half-turn behind.
        self.bus.execute(conversations.AppendTurn(thread_id=thread_id, turn=turn, messages=finished.messages))

    def _request_approval(self, thread_id: str, expense: ExpenseView) -> str:
        """Record a new delete card for this thread, showing `expense`, and return its id.

        The web panel calls this (as its `request_approval`) just before it sends the card. The id is random,
        so it can't be guessed from another card's; the record is committed at once, on its own.
        """
        approval_id = f"{APPROVAL_PREFIX}_{uuid4().hex}"
        self.bus.execute(
            RequestApproval(thread_id=thread_id, approval_id=approval_id, expense=ExpenseSnapshot.of(expense))
        )
        return approval_id

    def _answer(self, thread_id: str, text: str, today: date, surface: Surface) -> Iterator[AgentEvent]:
        """Answer one message in a thread on `surface`, saving the turn when it finishes. Yields its events."""
        turn = self._next_turn(thread_id)
        # Only the last few turns are sent. Older ones stay stored, but the model no longer sees them.
        # Whole turns, so a tool call is never cut off from its result.
        history = self.bus.ask(conversations.GetHistory(thread_id=thread_id, from_turn=turn - MAX_HISTORY_TURNS))
        for event in Agent(llm=self.llm, tools=self.tools).run(text, today, history, surface):
            if isinstance(event, TurnFinished):
                self._save(thread_id, turn, event)
            yield event

    def run_turn(self, thread_id: str, text: str, today: date) -> Iterator[AgentEvent]:
        """Answer one message in the web panel (an unknown thread starts a new conversation).

        There, forms and cards are shown, and every delete waits for the user's Approve on a card
        recorded in this thread.
        """
        panel = WebPanel(request_approval=lambda expense: self._request_approval(thread_id, expense))
        return self._answer(thread_id, text, today, panel)

    def decide(self, thread_id: str, approval_id: str, approved: bool) -> Iterator[AgentEvent]:
        """Approve or Cancel on a delete card. WHAT gets deleted is the server's snapshot of that card.

        The whole decision (take the card, check, delete, save the turn) is carried out before the first
        event goes out. Nothing is left half done if the browser disconnects while reading, and on an error
        the card is put back at once, in this same thread.
        """
        card = self.bus.execute(TakeApproval(thread_id=thread_id, approval_id=approval_id))
        try:
            turn = self._next_turn(thread_id)
            events = list(approval_turn(card.expense if card else None, approved, self.tools))
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
        """POST /chat: the whole reply at once, in text only. Unlike AG-UI, the server names threads here.

        Returns the thread id and the finished turn. Raises NotFoundError for a thread id it doesn't know.
        """
        if thread_id is None:
            thread_id = new_thread_id()
        elif self.bus.ask(conversations.GetLastTurn(thread_id=thread_id)) is None:
            # A typo'd id should be an error, not a silent new conversation.
            raise NotFoundError(conversations.THREAD_NOT_FOUND.format(thread_id=thread_id))
        finished = None
        for event in self._answer(thread_id, message, today, TextChat()):
            if isinstance(event, TurnFinished):
                finished = event
        if finished is None:  # can't happen: the agent always ends with one
            raise RuntimeError(NO_RESULT)
        return thread_id, finished
