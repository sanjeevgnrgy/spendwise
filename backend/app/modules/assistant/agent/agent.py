"""The agent loop: the model decides which tools to call, we run them, and repeat until it answers.

Application layer. The agent has no tools of its own: it gets them from an ExpenseTools port
(tools/port.py), shows them to the model, and runs every call through it. It speaks only provider-neutral
messages (core/llm) through the ToolCallingModel port, and yields AgentEvents (events.py); how those reach
a user is someone else's job. What differs between text chat and the web panel (prompt rules, tool specs,
calls handled in place) comes from the Surface it's given (surfaces.py). The Assistant use case
(application/assistant.py) runs it, one turn at a time, in the request's language: the model is asked to reply in
it, and the form and the server's own closing lines are written in it. The Approve/Cancel decision, which never
asks the model, is application/decisions.py.
"""

import logging
from collections.abc import Generator, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from functools import partial
from typing import Protocol

from app.core import llm
from app.core.i18n import Language, text, translatable
from app.core.llm import (
    LlmError,
    LlmStream,
    Message,
    ReasoningEffort,
    ToolCall,
    ToolCallingModel,
    ToolResult,
    ToolSpec,
    UserText,
)
from app.modules.assistant import a2ui
from app.modules.assistant.agent.events import AgentEvent, FormRequested, TextDelta, ToolCallSummary, TurnFinished
from app.modules.assistant.agent.prompts import system_instruction
from app.modules.assistant.agent.surfaces import CallHandler, CallOutcome, Surface
from app.modules.assistant.agent.tool_runs import run_and_report
from app.modules.assistant.i18n import ChatText
from app.modules.assistant.tools.port import ExpenseTools, ToolsUnavailableError

logger = logging.getLogger(__name__)

# Each step is one round trip to the model. A cap stops a confused model from looping forever,
# burning quota and keeping the request open.
MAX_STEPS = 5
# Recording and looking up expenses is simple bookkeeping. With deeper thinking, a single step
# took 40-60+ seconds in testing; "low" keeps the conversation responsive.
REASONING_EFFORT = ReasoningEffort.LOW
# Separates text the agent says in a later step (or its closing line) from what it already said.
PARAGRAPH_BREAK = "\n\n"

# What the model is told after a form is put on screen (a tool result: English, like all it reads).
FORM_ON_SCREEN = "The form is on the user's screen; they will submit it."


@dataclass
class _Turn:
    """One turn in progress: its messages so far, the tools run, and the text the user has been shown."""

    messages: list[Message]
    tool_calls: list[ToolCallSummary] = field(default_factory=list)
    reply: str = ""  # all the text the user has been shown so far, across steps

    def say(self, text: str, continues: bool = False) -> TextDelta:
        """Add `text` to the reply and return it as the piece to send.

        A new paragraph (`continues` False) is set apart from anything already said by PARAGRAPH_BREAK,
        e.g. the answer after an earlier step's "Let me check."; `continues` marks a further piece of it.
        """
        if not continues and self.reply:
            text = PARAGRAPH_BREAK + text
        self.reply += text
        return TextDelta(text)

    def record(self, outcome: CallOutcome) -> None:
        """Add a call's result to the messages, and its summary (if any) to the tools run."""
        if outcome.summary is not None:
            self.tool_calls.append(outcome.summary)
        self.messages.append(outcome.result)

    def finished(self) -> TurnFinished:
        """The TurnFinished event for the turn as it stands."""
        return TurnFinished(reply=self.reply, tool_calls=self.tool_calls, messages=self.messages)

    def end_with(self, line: str) -> Iterator[AgentEvent]:
        """End the turn with the server's own closing line: yields it as text, then the TurnFinished.

        The line is stored as the model's answer, so the turn ends cleanly for the next message.
        """
        self.messages.append(llm.AssistantText(text=line))
        yield self.say(line)
        yield self.finished()


@dataclass(frozen=True)
class _Setup:
    """What one turn offers the model: the tool declarations, the system instruction, and the handlers of the calls
    carried out in place (the form, the surface's own, the extensions')."""

    specs: list[ToolSpec]
    instruction: str
    handlers: dict[str, CallHandler]


class Extension(Protocol):
    """More the model may do this turn, beside the expense tools: other agents (delegation/delegator.py) or skills
    (skills/skill_tool.py). Each gives its tools, their handlers, and the lines of instruction that go with them; none
    of the three when it has nothing to offer, so the model's input is then exactly as without it."""

    def specs(self) -> list[ToolSpec]:
        """Its tools (none if it has nothing to offer)."""
        ...

    def handlers(self) -> Mapping[str, CallHandler]:
        """The handlers that carry its tools' calls out."""
        ...

    def rules(self) -> list[str]:
        """Its lines of the system instruction (none if it offers no tool)."""
        ...


@dataclass(frozen=True)
class Agent:
    """Answers messages with a model, the expense tools and any extensions (other agents, skills). Cheap to build:
    the Assistant makes one per turn."""

    llm: ToolCallingModel
    tools: ExpenseTools
    extensions: Sequence[Extension] = ()

    def run(
        self, message: str, today: date, history: list[Message], surface: Surface, language: Language
    ) -> Iterator[AgentEvent]:
        """Answer one user message, as events: TextDelta pieces, tool events, cards and forms, and finally a
        TurnFinished with the whole reply, the tools used and the messages to store.

        `history` is the earlier conversation (oldest first); `surface` is where the user is (surfaces.py); `language`
        the request's. Raises LlmError if the model fails or answers with nothing; the turn then has no TurnFinished.
        """
        turn = _Turn(messages=[UserText(text=message)])
        logger.info("user message (%d characters, %d earlier messages)", len(message), len(history))
        logger.debug("  message: %s", message)
        try:
            setup = self._prepare(today, surface, language)
        except ToolsUnavailableError as exc:
            # Without tools the model could only guess, so answer honestly without asking it.
            logger.warning("tools unavailable, not calling the model: %s", exc)
            yield from turn.end_with(text(language, ChatText.TOOLS_UNAVAILABLE))
            return
        yield from self._steps(turn, history, setup, language)

    def _prepare(self, today: date, surface: Surface, language: Language) -> _Setup:
        """What this turn offers the model: the tools (the surface's choice of them, then the extensions'), the system
        instruction, and the calls handled in place. Raises ToolsUnavailableError if the tools can't be listed."""
        # What the assistant can do comes from the tools, not from this code.
        tool_specs = self.tools.specs()
        category_names = self.tools.category_names()
        specs = surface.tool_specs(tool_specs) + [spec for extension in self.extensions for spec in extension.specs()]
        # The extensions' rules only when they offer something: without them the instruction is as before.
        extra = [rule for extension in self.extensions for rule in extension.rules()]
        instruction = system_instruction(today, category_names, surface.prompt_rules(category_names), language, extra)
        # The form is shown on either surface: a model may ask for one even where the tool wasn't offered.
        form = partial(_show_form, category_names, today, language)
        handlers: dict[str, CallHandler] = {a2ui.SHOW_FORM_TOOL_NAME: form, **surface.call_handlers(self.tools)}
        for extension in self.extensions:
            handlers.update(extension.handlers())
        return _Setup(specs=specs, instruction=instruction, handlers=handlers)

    def _steps(self, turn: _Turn, history: list[Message], setup: _Setup, language: Language) -> Iterator[AgentEvent]:
        """Ask the model, carry out its calls, and repeat until it answers in text, a form ends the turn, or
        MAX_STEPS is reached (then the server's own closing line ends it)."""
        for step in range(1, MAX_STEPS + 1):
            logger.info("step %d/%d: asking the model", step, MAX_STEPS)
            response = yield from self._ask(turn, history, setup.specs, setup.instruction)
            calls = [m for m in response.messages if isinstance(m, ToolCall)]
            if not calls:
                if not response.text:
                    raise LlmError(translatable(ChatText.EMPTY_ANSWER))
                logger.info("step %d: answered in text, done", step)
                yield turn.finished()
                return
            ends_turn = False
            for call in calls:
                outcome = yield from self._handle(call, setup.handlers)
                turn.record(outcome)
                ends_turn = ends_turn or outcome.ends_turn
            if ends_turn:
                # Only a form ends a turn early: the user answers with it now, not in words. Asking the model
                # again would only say "please fill in the form" (and use up a request).
                yield from turn.end_with(text(language, ChatText.FORM_SHOWN))
                return

        logger.warning("stopped after %d steps without a final answer", MAX_STEPS)
        yield from turn.end_with(text(language, ChatText.TOO_MANY_STEPS))

    def _ask(
        self, turn: _Turn, history: list[Message], specs: list[ToolSpec], instruction: str
    ) -> Generator[TextDelta, None, LlmStream]:
        """One step: ask the model, stream its text to the user, add all it produced to the turn. Returns it."""
        # Stateless: every request carries the earlier history plus this turn so far.
        response = self.llm.stream_with_tools(history + turn.messages, specs, instruction, REASONING_EFFORT)
        for index, piece in enumerate(response):
            # The step's first piece starts a new paragraph if the model already said something earlier.
            yield turn.say(piece, continues=index > 0)
        # Every request resends the whole history, so input tokens grow as a conversation gets longer.
        logger.info("  tokens: %s in, %s out", response.usage.input_tokens, response.usage.output_tokens)
        # Everything the model produced (reasoning, calls, text) goes into the history unchanged.
        turn.messages += response.messages
        return response

    def _handle(self, call: ToolCall, handlers: Mapping[str, CallHandler]) -> Generator[AgentEvent, None, CallOutcome]:
        """Carry out one tool call: by its handler if it has one, else by running it as the model asked."""
        handler = handlers.get(call.name)
        if handler is not None:
            return (yield from handler(call))
        output = yield from run_and_report(self.tools, call.call_id, call.name, call.arguments)
        return CallOutcome.reported(call, output)


def _show_form(
    category_names: list[str], today: date, language: Language, call: ToolCall
) -> Generator[AgentEvent, None, CallOutcome]:
    """show_expense_form: put a form on screen, and end the turn after this step.

    The model's own form if it passes the checks, else the built-in one, in `language`. Not a tool the agent ran,
    so no summary; the model is told the form is on screen.
    """
    form, source = a2ui.expense_form_from_call(call.arguments, category_names, today, language)
    logger.info("  form shown (%s)", source)
    yield FormRequested(form=form, source=source)
    result = ToolResult(call_id=call.call_id, name=call.name, output=FORM_ON_SCREEN)
    return CallOutcome(result=result, summary=None, ends_turn=True)
