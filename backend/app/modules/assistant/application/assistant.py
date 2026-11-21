"""The assistant's use cases: answer a message, and carry out an Approve or Cancel.

Application layer. They load a thread's history from the conversations module, run the agent
(agent/agent.py) on the right surface (agent/surfaces.py), record approvals (approvals/), and save the turn
once it has finished. Both routes (/chat and /agent) use them; neither knows about the database or the tools.
Each is given the request's language: the agent replies in it, and everything the server writes is in it.

Everything goes through the bus in short, separate steps (read the history, record a card, save the
turn), never one transaction around the whole run: a model call can take a minute or two, and no
database session stays open while it does.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from app.core.agents import RemoteAgents
from app.core.cqrs import MessageBus
from app.core.errors import NotFoundError
from app.core.i18n import Language, translatable
from app.core.llm import ToolCallingModel
from app.core.skills import SkillLibrary
from app.modules import conversations, receipts
from app.modules.assistant.agent.agent import Agent
from app.modules.assistant.agent.events import AgentEvent, TurnFinished
from app.modules.assistant.agent.surfaces import Surface, TextChat, WebPanel
from app.modules.assistant.application.decisions import approval_turn
from app.modules.assistant.application.receipt_turn import receipt_turn
from app.modules.assistant.approvals import ExpenseSnapshot, RequestApproval, RestoreApproval, TakeApproval
from app.modules.assistant.delegation import AgentDirectory, Delegator
from app.modules.assistant.receipt_agent.port import ReceiptReader
from app.modules.assistant.skills import SkillTool
from app.modules.assistant.tools.port import ExpenseTools
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

    module.create_router builds it from the bus, the tools adapter, the language model, the receipts module's
    ReceiptFiles, the receipt reader (the receipt agent, over A2A), and the agents the model may delegate to (their
    directory and the remote agents, D206) and the skills (D208), and the routes (api/routes.py) call it:
    run_turn, read_receipt and decide through api/agui_stream.py for POST /agent, chat for POST /chat.
    """

    bus: MessageBus
    tools: ExpenseTools
    llm: ToolCallingModel
    receipt_files: receipts.ReceiptFiles
    receipt_reader: ReceiptReader
    directory: AgentDirectory
    agents: RemoteAgents
    skills: SkillLibrary

    def _next_turn(self, owner_id: int, thread_id: str) -> int:
        """The number the owner's thread's next turn gets: 1 for a new thread."""
        return (self.bus.ask(conversations.GetLastTurn(owner_id=owner_id, thread_id=thread_id)) or 0) + 1

    def _save(self, owner_id: int, thread_id: str, turn: int, finished: TurnFinished) -> None:
        """Store a finished turn's messages as turn number `turn` of the owner's thread, in one transaction."""
        # Saved only when the turn completed, so a failed run leaves no half-turn behind.
        save = conversations.AppendTurn(owner_id=owner_id, thread_id=thread_id, turn=turn, messages=finished.messages)
        self.bus.execute(save)

    def _request_approval(self, owner_id: int, thread_id: str, expense: ExpenseView) -> str:
        """Record a new delete card for the owner's thread, showing `expense`, and return its id.

        The web panel calls this (as its `request_approval`) just before it sends the card. The id is random,
        so it can't be guessed from another card's; the record is committed at once, on its own.
        """
        approval_id = f"{APPROVAL_PREFIX}_{uuid4().hex}"
        snapshot = ExpenseSnapshot.of(expense)
        self.bus.execute(
            RequestApproval(owner_id=owner_id, thread_id=thread_id, approval_id=approval_id, expense=snapshot)
        )
        return approval_id

    def _answer(
        self, owner_id: int, thread_id: str, text: str, today: date, surface: Surface, language: Language
    ) -> Iterator[AgentEvent]:
        """Answer one message in the owner's thread on `surface`, saving the turn when it finishes. Yields its
        events.

        The agent's tools act for the owner: whatever the model asks (even an id that's another person's, say
        from text injected into a message), it reads and changes only their expenses (D191). `language` is the
        request's: the model is asked to reply in it, and the server writes its own texts in it.
        """
        turn = self._next_turn(owner_id, thread_id)
        # Only the last few turns are sent. Older ones stay stored, but the model no longer sees them.
        # Whole turns, so a tool call is never cut off from its result.
        since = turn - MAX_HISTORY_TURNS
        history = self.bus.ask(conversations.GetHistory(owner_id=owner_id, thread_id=thread_id, from_turn=since))
        delegator = Delegator(self.directory, self.agents, self.bus, owner_id, thread_id, today)
        # An agent waiting for this person's answer here gets this message first, on its own task (D206); the
        # model then reads the message with what came of it.
        text = yield from delegator.resume(text)
        # Beside the expense tools: other agents to delegate to, and the skills to read (each offers nothing if empty).
        extensions = (delegator, SkillTool(self.skills))
        agent = Agent(llm=self.llm, tools=self.tools.acting_for(owner_id), extensions=extensions)
        for event in agent.run(text, today, history, surface, language):
            if isinstance(event, TurnFinished):
                self._save(owner_id, thread_id, turn, event)
            yield event

    def run_turn(
        self, owner_id: int, thread_id: str, text: str, today: date, language: Language
    ) -> Iterator[AgentEvent]:
        """Answer one of the owner's messages in the web panel, in `language`. A thread they don't have yet starts
        a new conversation, even if another person uses the same id: threads are per person (D190).

        There, forms and cards are shown, and every delete waits for the user's Approve on a card
        recorded in this thread.
        """
        panel = WebPanel(request_approval=lambda expense: self._request_approval(owner_id, thread_id, expense))
        return self._answer(owner_id, thread_id, text, today, panel, language)

    def read_receipt(
        self, owner_id: int, thread_id: str, receipt_id: int, message: str, today: date, language: Language
    ) -> Iterator[AgentEvent]:
        """A receipt attached in the web panel (with `message`, possibly empty): read it and offer it as the expense
        form, pre-filled, saving the turn when it finishes. No agent loop: a person confirms the form first.

        Raises NotFoundError for a receipt the owner doesn't have and ExternalServiceError if the receipt agent can't
        be reached or can't read it (receipt_turn.py).
        """
        turn = self._next_turn(owner_id, thread_id)
        tools = self.tools.acting_for(owner_id)
        files, reader = self.receipt_files, self.receipt_reader
        for event in receipt_turn(files, reader, tools, owner_id, receipt_id, message, today, language):
            if isinstance(event, TurnFinished):
                self._save(owner_id, thread_id, turn, event)
            yield event

    def decide(
        self, owner_id: int, thread_id: str, approval_id: str, approved: bool, language: Language
    ) -> Iterator[AgentEvent]:
        """Approve or Cancel on a delete card. WHAT gets deleted is the server's snapshot of that card.

        The whole decision (take the card, check, delete, save the turn) is carried out before the first
        event goes out. Nothing is left half done if the browser disconnects while reading, and on an error
        the card is put back at once, in this same thread. Only the owner's own card is found (another person's is
        unknown, D190), and the delete runs with tools acting for them. The reply is written in `language`.
        """
        card = self.bus.execute(TakeApproval(owner_id=owner_id, thread_id=thread_id, approval_id=approval_id))
        try:
            turn = self._next_turn(owner_id, thread_id)
            tools = self.tools.acting_for(owner_id)
            events = list(approval_turn(card.expense if card else None, approved, tools, language))
            finished = events[-1]
            assert isinstance(finished, TurnFinished)
            self._save(owner_id, thread_id, turn, finished)
        except Exception:
            if card is not None:
                # The decision failed midway: put the card back as it was, so pressing Approve again works.
                # If the expense was deleted after all, Approve's check will find it gone.
                logger.warning("approval %s not completed; putting the card back", approval_id)
                restore = RestoreApproval(owner_id=owner_id, thread_id=thread_id, approval_id=approval_id, card=card)
                self.bus.execute(restore)
            raise
        yield from events

    def chat(
        self, owner_id: int, message: str, thread_id: str | None, today: date, language: Language
    ) -> tuple[str, TurnFinished]:
        """POST /chat: the whole reply at once, in text only. Unlike AG-UI, the server names threads here.

        The model is asked to reply in `language`, and the server writes its own texts in it. Returns the thread id
        and the finished turn. Raises NotFoundError for a thread id the owner doesn't have (another person's
        included: it isn't revealed, D190).
        """
        if thread_id is None:
            thread_id = new_thread_id()
        elif self.bus.ask(conversations.GetLastTurn(owner_id=owner_id, thread_id=thread_id)) is None:
            # A typo'd id should be an error, not a silent new conversation.
            raise NotFoundError(translatable(conversations.ConversationText.THREAD_NOT_FOUND, thread_id=thread_id))
        finished = None
        for event in self._answer(owner_id, thread_id, message, today, TextChat(), language):
            if isinstance(event, TurnFinished):
                finished = event
        if finished is None:  # can't happen: the agent always ends with one
            raise RuntimeError(NO_RESULT)
        return thread_id, finished
