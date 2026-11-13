"""The Gemini adapter: the only code that knows Gemini's API and its wire format.

It translates SpendWise's provider-neutral messages and tool specs (messages.py) into Gemini's
Interactions API "steps" and back. Swapping providers means writing another file like this one.
"""

import json
import logging
from collections import defaultdict
from collections.abc import Iterator
from enum import StrEnum
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.llm.messages import (
    AssistantText,
    Message,
    Reasoning,
    ReasoningEffort,
    ToolCall,
    ToolResult,
    ToolSpec,
    Usage,
    UserText,
)
from app.core.llm.port import LlmError

logger = logging.getLogger(__name__)

PROVIDER = "gemini"


# ---------- Gemini's wire format ----------


class _Step(StrEnum):
    USER_INPUT = "user_input"
    MODEL_OUTPUT = "model_output"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"
    THOUGHT = "thought"


class _Event(StrEnum):
    STEP_START = "step.start"
    STEP_DELTA = "step.delta"
    COMPLETED = "interaction.completed"
    ERROR = "error"


class _Delta(StrEnum):
    TEXT = "text"
    ARGUMENTS = "arguments_delta"
    THOUGHT_SIGNATURE = "thought_signature"


TEXT_PART = "text"
SIGNATURE = "signature"
# The only JSON-schema keywords passed on to Gemini; the rest (title, default, ...) are noise to it.
_KEPT_SCHEMA_KEYWORDS = ("type", "description", "enum", "items", "format")


def _text_content(text: str) -> list[dict[str, str]]:
    return [{"type": TEXT_PART, "text": text}]


def _joined_text(parts: list[dict[str, Any]] | None) -> str:
    return "".join(part.get("text", "") for part in parts or [] if part.get("type") == TEXT_PART)


def to_steps(messages: list[Message]) -> list[dict[str, Any]]:
    """Neutral messages -> Gemini steps (the history Gemini expects with every request)."""
    steps: list[dict[str, Any]] = []
    for message in messages:
        match message:
            case UserText(text=text):
                steps.append({"type": _Step.USER_INPUT, "content": _text_content(text)})
            case AssistantText(text=text):
                steps.append({"type": _Step.MODEL_OUTPUT, "content": _text_content(text)})
            case ToolCall(call_id=call_id, name=name, arguments=arguments):
                steps.append({"type": _Step.FUNCTION_CALL, "id": call_id, "name": name, "arguments": arguments})
            case ToolResult(call_id=call_id, name=name, output=output, is_error=is_error):
                steps.append(
                    {"type": _Step.FUNCTION_RESULT, "call_id": call_id, "name": name, "is_error": is_error,
                     "result": _text_content(output)}
                )
            case Reasoning(provider=provider, opaque=opaque) if provider == PROVIDER:
                # Gemini needs its own thoughts back (with their signature) to carry on after a tool call.
                steps.append({"type": _Step.THOUGHT, **opaque})
            case Reasoning():
                pass  # another provider's reasoning means nothing to Gemini
    return steps


def from_steps(steps: list[dict[str, Any]]) -> list[Message]:
    """Gemini steps -> neutral messages. Step types we don't use are skipped."""
    messages: list[Message] = []
    for step in steps:
        match step.get("type"):
            case _Step.USER_INPUT:
                messages.append(UserText(text=_joined_text(step.get("content"))))
            case _Step.MODEL_OUTPUT:
                messages.append(AssistantText(text=_joined_text(step.get("content"))))
            case _Step.FUNCTION_CALL:
                messages.append(ToolCall(call_id=step["id"], name=step["name"], arguments=step.get("arguments") or {}))
            case _Step.FUNCTION_RESULT:
                messages.append(
                    ToolResult(call_id=step["call_id"], name=step["name"], output=_joined_text(step.get("result")),
                               is_error=bool(step.get("is_error")))
                )
            case _Step.THOUGHT:
                opaque = {key: value for key, value in step.items() if key != "type" and value is not None}
                messages.append(Reasoning(provider=PROVIDER, opaque=opaque))
            case other:
                logger.warning("skipping a Gemini step of unknown type %r", other)
    return messages


def _simplify_schema(prop: dict[str, Any]) -> dict[str, Any]:
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


# ---------- the client ----------


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    if settings.gemini_api_key is None:
        # Say exactly what to fix, instead of letting a vague SDK error surface later.
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env in the project folder (see .env.example).")
    # Built once on first use and then reused, so all requests share one connection pool.
    # The key is passed explicitly because the SDK would silently prefer GOOGLE_API_KEY
    # over GEMINI_API_KEY if both happened to be set on this machine.
    return genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        # The SDK's defaults (5 attempts, waits of up to 60 s) can leave a request hanging for
        # many minutes while Gemini is down. Give up on an attempt after 60 s and try at most
        # twice. 60 s, not less: a function-calling step can take 20-30 s while the model thinks.
        http_options=types.HttpOptions(
            timeout=60_000,  # milliseconds
            retry_options=types.HttpRetryOptions(
                attempts=2,
                # Retry only when Google's side failed (5xx), e.g. "high demand". Never on 429 (quota used
                # up): the SDK then sleeps for as long as Google's retry-after-ms header asks, with no upper
                # limit and no timeout, so the request looked hung. Failing at once shows the quota message.
                http_status_codes=[500, 502, 503, 504],
            ),
        ),
    )


def _create(**request: Any) -> Any:
    """Send one request to Gemini. Returns the whole interaction, or with stream=True, an event iterator."""
    # Outside the try below: a missing setting is our misconfiguration, not a Gemini failure.
    client = _client()
    if not settings.gemini_model:
        raise RuntimeError("GEMINI_MODEL is not set. Add it to .env in the project folder (see .env.example).")
    try:
        return client.interactions.create(
            model=settings.gemini_model,
            # Don't let Google keep this conversation for later retrieval; we don't need it.
            # (On the free tier, Google's data-use terms still apply to what we send.)
            store=False,
            **request,
        )
    except Exception as exc:
        # google-genai 3.3.0 doesn't publicly export the Interactions API's error class,
        # so catch broadly, but only around this single network call.
        raise LlmError(str(exc)) from exc


def _ask_for_json(prompt: str, schema: dict[str, Any], system_instruction: str) -> str:
    interaction = _create(
        input=prompt,
        system_instruction=system_instruction,
        # Gemini can only produce output that fits this JSON schema ("constrained decoding"),
        # so we get the fields and types we asked for instead of free-form prose.
        response_format={"type": "text", "mime_type": "application/json", "schema": schema},
    )
    if not interaction.output_text:
        raise LlmError("Gemini returned no text.")
    return interaction.output_text


class GeminiStream:
    """One Gemini response, streamed.

    Loop over it to get the answer's text piece by piece, as Gemini writes it. Gemini streams every
    step in pieces (thoughts and function calls too), so this also puts them back together: once the
    loop has ended, `.messages` holds everything the model produced, as neutral messages, and `.usage`
    the token counts.
    """

    def __init__(self, events: Any) -> None:
        self._events = events  # the SDK's event stream: one parsed Server-Sent Event per item
        self.text = ""
        self.messages: list[Message] = []
        self.usage = Usage()

    def __iter__(self) -> Iterator[str]:
        steps: dict[int, dict[str, Any]] = {}  # each step under its index; every delta names the index it extends
        pieces: dict[int, list[str]] = defaultdict(list)
        try:
            # `with` closes the HTTP connection even if the caller stops reading early.
            with self._events:
                for event in self._events:
                    kind = getattr(event, "event_type", None)
                    if kind == _Event.STEP_START:
                        # The step's outline: its type and, for a function call, the name and id.
                        steps[event.index] = event.step.model_dump()
                    elif kind == _Event.STEP_DELTA:
                        delta = event.delta
                        if delta.type == _Delta.TEXT and delta.text:
                            # The answer itself. Thoughts arrive as other delta types, so they never reach the user.
                            pieces[event.index].append(delta.text)
                            self.text += delta.text
                            yield delta.text
                        elif delta.type == _Delta.ARGUMENTS:
                            # A function call's arguments arrive as fragments of one JSON string.
                            pieces[event.index].append(delta.arguments or "")
                        elif delta.type == _Delta.THOUGHT_SIGNATURE:
                            pieces[event.index].append(delta.signature or "")
                        # Other deltas (e.g. thought summaries, which we don't ask for) are skipped, as Google advises.
                    elif kind == _Event.COMPLETED:
                        # Unlike a non-streamed response, this final event doesn't repeat the steps.
                        usage = event.interaction.usage
                        if usage is not None:
                            self.usage = Usage(
                                input_tokens=usage.total_input_tokens, output_tokens=usage.total_output_tokens
                            )
                    elif kind == _Event.ERROR:
                        raise LlmError(event.error.message if event.error else "Gemini reported an error.")
            finished = [_finish_step(steps[index], "".join(pieces[index])) for index in sorted(steps)]
            self.messages = from_steps(finished)
        except LlmError:
            raise
        except Exception as exc:
            # The connection broke mid-answer, or the arguments weren't valid JSON.
            raise LlmError(str(exc)) from exc


def _finish_step(step: dict[str, Any], streamed: str) -> dict[str, Any]:
    """Put a step's streamed pieces where a non-streamed response has them."""
    if step["type"] == _Step.MODEL_OUTPUT and streamed:
        step["content"] = _text_content(streamed)
    elif step["type"] == _Step.FUNCTION_CALL and streamed:
        step["arguments"] = json.loads(streamed)
    elif step["type"] == _Step.THOUGHT and streamed:
        step[SIGNATURE] = streamed
    return step


def _stream_with_tools(
    history: list[Message], tools: list[ToolSpec], system_instruction: str, effort: ReasoningEffort | None = None
) -> GeminiStream:
    """`history` is the whole conversation so far (we don't let Google store it, so it's resent every
    time). The answer may be text, tool calls, or both: loop over the result for the text as it
    arrives, then read `.messages` for everything, including any tool calls.
    """
    request: dict[str, Any] = {
        "input": to_steps(history),
        "tools": [to_declaration(tool) for tool in tools],
        "system_instruction": system_instruction,
    }
    if effort:
        request["generation_config"] = {"thinking_level": effort.value}
    # The request is sent now; the answer is read as the caller loops over the stream.
    return GeminiStream(_create(stream=True, **request))


class GeminiModel:
    """The LanguageModel port (port.py), answered by Gemini. Built once, by the composition root."""

    def ask_for_json(self, prompt: str, schema: dict[str, Any], system_instruction: str) -> str:
        return _ask_for_json(prompt, schema, system_instruction)

    def stream_with_tools(
        self,
        history: list[Message],
        tools: list[ToolSpec],
        system_instruction: str,
        effort: ReasoningEffort | None = None,
    ) -> GeminiStream:
        return _stream_with_tools(history, tools, system_instruction, effort)
