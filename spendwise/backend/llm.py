import os
from functools import lru_cache

from google import genai


class GeminiError(Exception):
    """Gemini was called but couldn't give an answer (bad key, quota, model error, network...)."""


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        # Say exactly what to fix, instead of letting a vague SDK error surface later.
        raise RuntimeError(f"{name} is not set. Add it to spendwise/.env (see .env.example).")
    return value


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    # Built once on first use and then reused, so all requests share one connection pool.
    # The key is passed explicitly because the SDK would silently prefer GOOGLE_API_KEY
    # over GEMINI_API_KEY if both happened to be set on this machine.
    return genai.Client(api_key=_require_env("GEMINI_API_KEY"))


def ask_gemini(prompt: str) -> str:
    """Send one prompt to Gemini and return its text answer."""
    # Outside the try below: a missing setting is our misconfiguration, not a Gemini failure.
    client = _client()
    model = _require_env("GEMINI_MODEL")

    try:
        interaction = client.interactions.create(
            model=model,
            input=prompt,
            # By default Google keeps every request and answer (1 day free tier, 55 days paid).
            # We don't need server-side history, and later prompts will contain spending data.
            store=False,
        )
    except Exception as exc:
        # google-genai 3.3.0 doesn't publicly export the Interactions API's error class,
        # so catch broadly, but only around this single network call.
        raise GeminiError(str(exc)) from exc

    if not interaction.output_text:
        raise GeminiError("Gemini returned no text.")
    return interaction.output_text
