"""The only code that talks to Gemini. Everything else calls the functions below."""

from functools import lru_cache
from typing import Any

from google import genai
from google.genai import interactions, types

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
            retry_options=types.HttpRetryOptions(attempts=2),
        ),
    )


def _create(**request: Any) -> interactions.Interaction:
    """Send one request to Gemini and return the whole interaction (text and any function calls)."""
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


def ask_gemini_with_tools(
    history: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    system_instruction: str,
    thinking_level: str | None = None,
) -> interactions.Interaction:
    """One step of a function-calling conversation.

    `history` is the whole conversation so far (we don't let Google store it, so it's resent every
    time). Returns the whole interaction, because the answer may be function calls
    (`interaction.steps`) rather than text (`interaction.output_text`).
    `thinking_level` ("minimal", "low", "medium", "high", "xhigh") trades reasoning depth for speed.
    """
    request: dict[str, Any] = {"input": history, "tools": tools, "system_instruction": system_instruction}
    if thinking_level:
        request["generation_config"] = {"thinking_level": thinking_level}
    return _create(**request)
