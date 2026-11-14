"""Gemini's wire format as plain data: the translating half of the Gemini adapter (infrastructure).

Gemini's Interactions API speaks in "steps" (user input, model output, function calls and their results,
thoughts), sent as JSON-like dicts and streamed back in pieces. This file turns SpendWise's provider-neutral
messages and tool specs (messages.py) into those dicts and back, and puts a streamed answer's pieces back
together. It never imports Google's SDK, so all of it works on plain values.

Used only by gemini.py, which keeps the SDK calls, the timeouts and retries, and the error mapping.
"""

import json
import logging
from collections import defaultdict
from enum import StrEnum
from typing import Any

from app.core.llm.messages import AssistantText, Message, Reasoning, ToolCall, ToolResult, ToolSpec, UserText

logger = logging.getLogger(__name__)

# The provider name stored with Gemini's reasoning (messages.Reasoning), so it's only ever sent back to Gemini.
PROVIDER = "gemini"


# A step's "type" on the wire.
class StepType(StrEnum):
    USER_INPUT = "user_input"
    MODEL_OUTPUT = "model_output"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"
    THOUGHT = "thought"


# A streamed event's "event_type".
class EventType(StrEnum):
    STEP_START = "step.start"
    STEP_DELTA = "step.delta"
    COMPLETED = "interaction.completed"
    ERROR = "error"


# A step.delta's "type": which attribute holds the streamed piece.
class DeltaType(StrEnum):
    TEXT = "text"
    ARGUMENTS = "arguments_delta"
    THOUGHT_SIGNATURE = "thought_signature"


TEXT_PART = "text"
SIGNATURE = "signature"
# The only JSON-schema keywords passed on to Gemini; the rest (title, default, ...) are noise to it.
_KEPT_SCHEMA_KEYWORDS = ("type", "description", "enum", "items", "format")


def _text_content(text: str) -> list[dict[str, str]]:
    """Text as Gemini's content: a list with one text part."""
    return [{"type": TEXT_PART, "text": text}]


def _joined_text(parts: list[dict[str, Any]] | None) -> str:
    """All the text parts of Gemini content, joined; other parts (and None) give ""."""
    return "".join(part.get("text", "") for part in parts or [] if part.get("type") == TEXT_PART)


def to_steps(messages: list[Message]) -> list[dict[str, Any]]:
    """Neutral messages -> Gemini steps (the history Gemini expects with every request)."""
    steps: list[dict[str, Any]] = []
    for message in messages:
        match message:
            case UserText(text=text):
                steps.append({"type": StepType.USER_INPUT, "content": _text_content(text)})
            case AssistantText(text=text):
                steps.append({"type": StepType.MODEL_OUTPUT, "content": _text_content(text)})
            case ToolCall(call_id=call_id, name=name, arguments=arguments):
                steps.append({"type": StepType.FUNCTION_CALL, "id": call_id, "name": name, "arguments": arguments})
            case ToolResult(call_id=call_id, name=name, output=output, is_error=is_error):
                steps.append(
                    {"type": StepType.FUNCTION_RESULT, "call_id": call_id, "name": name, "is_error": is_error,
                     "result": _text_content(output)}
                )
            case Reasoning(provider=provider, opaque=opaque) if provider == PROVIDER:
                # Gemini needs its own thoughts back (with their signature) to carry on after a tool call.
                steps.append({"type": StepType.THOUGHT, **opaque})
            case Reasoning():
                pass  # another provider's reasoning means nothing to Gemini
    return steps


def from_steps(steps: list[dict[str, Any]]) -> list[Message]:
    """Gemini steps -> neutral messages. Step types we don't use are skipped, with a warning in the log."""
    messages: list[Message] = []
    for step in steps:
        match step.get("type"):
            case StepType.USER_INPUT:
                messages.append(UserText(text=_joined_text(step.get("content"))))
            case StepType.MODEL_OUTPUT:
                messages.append(AssistantText(text=_joined_text(step.get("content"))))
            case StepType.FUNCTION_CALL:
                messages.append(ToolCall(call_id=step["id"], name=step["name"], arguments=step.get("arguments") or {}))
            case StepType.FUNCTION_RESULT:
                messages.append(
                    ToolResult(call_id=step["call_id"], name=step["name"], output=_joined_text(step.get("result")),
                               is_error=bool(step.get("is_error")))
                )
            case StepType.THOUGHT:
                opaque = {key: value for key, value in step.items() if key != "type" and value is not None}
                messages.append(Reasoning(provider=PROVIDER, opaque=opaque))
            case other:
                logger.warning("skipping a Gemini step of unknown type %r", other)
    return messages


def _simplify_schema(prop: dict[str, Any]) -> dict[str, Any]:
    """One argument's JSON schema, cut down to the keywords Gemini uses (_KEPT_SCHEMA_KEYWORDS)."""
    # Optional arguments arrive as anyOf [X, null]; Gemini just needs X (and "not required").
    if "anyOf" in prop:
        real = next((option for option in prop["anyOf"] if option.get("type") != "null"), {})
        prop = {**prop, **real}
    return {key: prop[key] for key in _KEPT_SCHEMA_KEYWORDS if key in prop}


def to_declaration(spec: ToolSpec) -> dict[str, Any]:
    """A neutral tool spec -> a Gemini function declaration."""
    schema = spec.parameters
    return {
        "type": "function",
        "name": spec.name,
        "description": spec.description,
        "parameters": {
            "type": "object",
            "properties": {name: _simplify_schema(prop) for name, prop in schema.get("properties", {}).items()},
            "required": schema.get("required", []),
        },
    }


def finish_step(step: dict[str, Any], streamed: str) -> dict[str, Any]:
    """Put a step's streamed pieces where a non-streamed response has them, and return the step (changed in place).

    Raises ValueError (json.JSONDecodeError) if a function call's streamed arguments aren't valid JSON.
    """
    if step["type"] == StepType.MODEL_OUTPUT and streamed:
        step["content"] = _text_content(streamed)
    elif step["type"] == StepType.FUNCTION_CALL and streamed:
        step["arguments"] = json.loads(streamed)
    elif step["type"] == StepType.THOUGHT and streamed:
        step[SIGNATURE] = streamed
    return step


class StepAssembler:
    """Puts a streamed answer's steps back together.

    Gemini streams every step in pieces, thoughts and function calls too: first its outline (a step.start
    event: its type and, for a function call, the name and id), then pieces (step.delta events), each naming
    the index of the step it extends. Feed it those events in order; once the stream has ended, messages()
    gives everything the model produced.
    """

    def __init__(self) -> None:
        """An assembler with no steps yet: one per streamed answer."""
        self._steps: dict[int, dict[str, Any]] = {}  # each step's outline, under its index
        self._pieces: dict[int, list[str]] = defaultdict(list)  # each step's streamed pieces, in order

    def start(self, index: int, step: dict[str, Any]) -> None:
        """Record step `index`'s outline (a step.start event's step, as a dict)."""
        self._steps[index] = step

    def add(self, index: int, delta: Any) -> str | None:
        """Add one streamed piece (a step.delta event's delta) to step `index`.

        Returns the piece if it's text of the answer, for the caller to pass on to the user; None otherwise.
        `delta.type` (a DeltaType) says which attribute holds the piece; other delta types are skipped.
        """
        match delta.type:
            case DeltaType.TEXT if delta.text:
                # The answer itself. Thoughts arrive as other delta types, so they never reach the user.
                self._pieces[index].append(delta.text)
                return delta.text
            case DeltaType.ARGUMENTS:
                # A function call's arguments arrive as fragments of one JSON string.
                self._pieces[index].append(delta.arguments or "")
            case DeltaType.THOUGHT_SIGNATURE:
                self._pieces[index].append(delta.signature or "")
            # Other deltas (e.g. thought summaries, which we don't ask for) are skipped, as Google advises.
        return None

    def messages(self) -> list[Message]:
        """Every step, finished and in index order, as neutral messages.

        Unlike a non-streamed response, the stream's final event doesn't repeat the steps, so this is the only
        record of them. Raises ValueError if a function call's arguments aren't valid JSON.
        """
        finished = [finish_step(self._steps[index], "".join(self._pieces[index])) for index in sorted(self._steps)]
        return from_steps(finished)
