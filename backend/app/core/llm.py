"""The only code that talks to Gemini. Everything else calls the functions below."""

import json
from collections import defaultdict
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.errors import ExternalServiceError


class GeminiError(ExternalServiceError):
    """Gemini was called but couldn't give a usable answer (bad key, quota, model error, network...)."""


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
    """Send one request to Gemini. Returns the whole interaction (text and any function calls),
    or with stream=True, an iterator of streaming events."""
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
        raise GeminiError(str(exc)) from exc


def _interact(**request: Any) -> str:
    """Send one request to Gemini and return its text output."""
    interaction = _create(**request)
    if not interaction.output_text:
        raise GeminiError("Gemini returned no text.")
    return interaction.output_text


def ask_gemini(prompt: str) -> str:
    """Send one prompt to Gemini and return its free-text answer."""
    return _interact(input=prompt)


def ask_gemini_for_json(prompt: str, schema: dict[str, Any], system_instruction: str) -> str:
    """Structured output: Gemini's answer is JSON shaped by `schema`. Returns the JSON text."""
    return _interact(
        input=prompt,
        system_instruction=system_instruction,
        # Gemini can only produce output that fits this JSON schema ("constrained decoding"),
        # so we get the fields and types we asked for instead of free-form prose.
        response_format={"type": "text", "mime_type": "application/json", "schema": schema},
    )


class GeminiStream:
    """One Gemini response, streamed.

    Loop over it to get the answer's text piece by piece, as Gemini writes it. Gemini streams every
    step of its response in pieces (thoughts and function calls too), so this also puts the steps
    back together: once the loop has ended, `.steps` holds them in the same form a non-streamed
    response has, ready to be resent as history, and `.usage` holds the token counts.
    """

    def __init__(self, events: Any) -> None:
        self._events = events  # the SDK's event stream: one parsed Server-Sent Event per item
        self.text = ""
        self.steps: list[dict[str, Any]] = []
        self.usage: Any = None

    def __iter__(self) -> Iterator[str]:
        steps: dict[int, dict[str, Any]] = {}  # each step under its index; every delta names the index it extends
        pieces: dict[int, list[str]] = defaultdict(list)
        try:
            # `with` closes the HTTP connection even if the caller stops reading early.
            with self._events:
                for event in self._events:
                    kind = getattr(event, "event_type", None)
                    if kind == "step.start":
                        # The step's outline: its type and, for a function call, the name and id.
                        steps[event.index] = event.step.model_dump()
                    elif kind == "step.delta":
                        delta = event.delta
                        if delta.type == "text" and delta.text:
                            # The answer itself. Thoughts arrive as other delta types, so they never reach the user.
                            pieces[event.index].append(delta.text)
                            self.text += delta.text
                            yield delta.text
                        elif delta.type == "arguments_delta":
                            # A function call's arguments arrive as fragments of one JSON string.
                            pieces[event.index].append(delta.arguments or "")
                        elif delta.type == "thought_signature":
                            # Gemini needs this back in the history to carry on reasoning after a tool call.
                            pieces[event.index].append(delta.signature or "")
                        # Other deltas (e.g. thought summaries, which we don't ask for) are skipped, as Google advises.
                    elif kind == "interaction.completed":
                        # Unlike a non-streamed response, this final event doesn't repeat the steps.
                        self.usage = event.interaction.usage
                    elif kind == "error":
                        raise GeminiError(event.error.message if event.error else "Gemini reported an error.")
            self.steps = [_finish_step(steps[index], "".join(pieces[index])) for index in sorted(steps)]
        except GeminiError:
            raise
        except Exception as exc:
            # The connection broke mid-answer, or the arguments weren't valid JSON.
            raise GeminiError(str(exc)) from exc


def _finish_step(step: dict[str, Any], streamed: str) -> dict[str, Any]:
    """Put a step's streamed pieces where a non-streamed response has them."""
    if step["type"] == "model_output" and streamed:
        step["content"] = [{"type": "text", "text": streamed}]
    elif step["type"] == "function_call" and streamed:
        step["arguments"] = json.loads(streamed)
    elif step["type"] == "thought" and streamed:
        step["signature"] = streamed
    return step


def stream_gemini_with_tools(
    history: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    system_instruction: str,
    thinking_level: str | None = None,
) -> GeminiStream:
    """One step of a function-calling conversation, streamed.

    `history` is the whole conversation so far (we don't let Google store it, so it's resent every
    time). The answer may be text, function calls, or both: loop over the result for the text as it
    arrives, then read `.steps` for everything, including any function calls.
    `thinking_level` ("minimal", "low", "medium", "high", "xhigh") trades reasoning depth for speed.
    """
    request: dict[str, Any] = {"input": history, "tools": tools, "system_instruction": system_instruction}
    if thinking_level:
        request["generation_config"] = {"thinking_level": thinking_level}
    # The request is sent now; the answer is read as the caller loops over the stream.
    return GeminiStream(_create(stream=True, **request))
