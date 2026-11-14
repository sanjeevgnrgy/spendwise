"""The agent loop: the model decides which tools to call, we run them, and repeat until it answers.

Application layer. The agent has no tools of its own: it gets them from an ExpenseTools port
(tools/port.py), shows them to the model, and runs every call through it. It speaks only provider-neutral
messages (core/llm) through the ToolCallingModel port, and yields AgentEvents (events.py); how those reach
a user is someone else's job. What differs between text chat and the web panel (prompt rules, tool specs,
calls handled in place) comes from the Surface it's given (surfaces.py). The Assistant use case
(application/assistant.py) runs it, one turn at a time; the Approve/Cancel decision, which never asks the
model, is application/decisions.py.
"""

import logging
from collections.abc import Generator, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date
from functools import partial

from app.core.llm import (
    AssistantText,
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

TOO_MANY_STEPS = "Sorry, that took too many steps, so I stopped. Could you try a simpler or more specific request?"
FORM_SHOWN = "Please check the details in the form and press Save."
FORM_ON_SCREEN = "The form is on the user's screen; they will submit it."
TOOLS_UNAVAILABLE = (
    "Sorry, I can't reach the expense tools right now, so I can't look up or change anything. "
    "Please try again in a moment."
)
EMPTY_ANSWER = "The model returned neither text nor a tool call."


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

    def end_with(self, text: str) -> Iterator[AgentEvent]:
        """End the turn with the server's own closing line: yields it as text, then the TurnFinished.

        The line is stored as the model's answer, so the turn ends cleanly for the next message.
        """
        self.messages.append(AssistantText(text=text))
        yield self.say(text)
        yield self.finished()


@dataclass(frozen=True)
class Agent:
    """Answers messages with a model and the expense tools. Cheap to build: the Assistant makes one per turn."""

    llm: ToolCallingModel
    tools: ExpenseTools

    def run(self, message: str, today: date, history: list[Message], surface: Surface) -> Iterator[AgentEvent]:
        """Answer one user message, as events: TextDelta pieces, tool events, cards and forms, and finally a
        TurnFinished with the whole reply, the tools used and the messages to store.

        `history` is the earlier conversation (oldest first); `surface` is where the user is (surfaces.py).
        Raises LlmError if the model fails or answers with nothing; the turn then has no TurnFinished.
        """
        turn = _Turn(messages=[UserText(text=message)])
        logger.info("user message (%d characters, %d earlier messages)", len(message), len(history))
        logger.debug("  message: %s", message)
        try:
            # What the assistant can do comes from the tools, not from this code.
            specs = self.tools.specs()
            category_names = self.tools.category_names()
        except ToolsUnavailableError as exc:
            # Without tools the model could only guess, so answer honestly without asking it.
            logger.warning("tools unavailable, not calling the model: %s", exc)
            yield from turn.end_with(TOOLS_UNAVAILABLE)
            return
        specs = surface.tool_specs(specs)
        instruction = system_instruction(today, category_names, surface.prompt_rules(category_names))
        # The form is shown on either surface: a model may ask for one even where the tool wasn't offered.
        form = partial(_show_form, category_names, today)
        handlers: Mapping[str, CallHandler] = {a2ui.SHOW_FORM_TOOL_NAME: form, **surface.call_handlers(self.tools)}

        for step in range(1, MAX_STEPS + 1):
            logger.info("step %d/%d: asking the model", step, MAX_STEPS)
            response = yield from self._ask(turn, history, specs, instruction)
            calls = [m for m in response.messages if isinstance(m, ToolCall)]
            if not calls:
                if not response.text:
                    raise LlmError(EMPTY_ANSWER)
                logger.info("step %d: answered in text, done", step)
                yield turn.finished()
                return
            ends_turn = False
            for call in calls:
                outcome = yield from self._handle(call, handlers)
                turn.record(outcome)
                ends_turn = ends_turn or outcome.ends_turn
            if ends_turn:
                # Only a form ends a turn early: the user answers with it now, not in words. Asking the model
                # again would only say "please fill in the form" (and use up a request).
                yield from turn.end_with(FORM_SHOWN)
                return

        logger.warning("stopped after %d steps without a final answer", MAX_STEPS)
        yield from turn.end_with(TOO_MANY_STEPS)

    def _ask(
        self, turn: _Turn, history: list[Message], specs: list[ToolSpec], instruction: str
    ) -> Generator[TextDelta, None, LlmStream]:
        """One step: ask the model, stream its text to the user, add all it produced to the turn. Returns it."""
        # Stateless: every request carries the earlier history plus this turn so far.
        response = self.llm.stream_with_tools(history + turn.messages, specs, instruction, REASONING_EFFORT)
        for index, text in enumerate(response):
            # The step's first piece starts a new paragraph if the model already said something earlier.
            yield turn.say(text, continues=index > 0)
        # Every request resends the whole history, so input tokens grow as a conversation gets longer.
        logger.info("  tokens: %s in, %s out", response.usage.input_tokens, response.usage.output_tokens)
        # Everything the model produced (reasoning, calls, text) goes into the history unchanged.
        turn.messages += response.messages
        return response

    def _handle(
        self, call: ToolCall, handlers: Mapping[str, CallHandler]
    ) -> Generator[AgentEvent, None, CallOutcome]:
        """Carry out one tool call: by its handler if it has one, else by running it as the model asked."""
        handler = handlers.get(call.name)
        if handler is not None:
            return (yield from handler(call))
        output = yield from run_and_report(self.tools, call.call_id, call.name, call.arguments)
        return CallOutcome.reported(call, output)


def _show_form(category_names: list[str], today: date, call: ToolCall) -> Generator[AgentEvent, None, CallOutcome]:
    """show_expense_form: put a form on screen, and end the turn after this step.

    The model's own form if it passes the checks, else the built-in one. Not a tool the agent ran, so no
    summary; the model is told the form is on screen.
    """
    form, source = a2ui.expense_form_from_call(call.arguments, category_names, today)
    logger.info("  form shown (%s)", source)
    yield FormRequested(form=form, source=source)
    result = ToolResult(call_id=call.call_id, name=call.name, output=FORM_ON_SCREEN)
    return CallOutcome(result=result, summary=None, ends_turn=True)
