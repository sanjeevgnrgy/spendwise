from functools import lru_cache

from google import genai

from app.core.config import settings


class GeminiError(Exception):
    """Gemini was called but couldn't give an answer (bad key, quota, model error, network...)."""


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    if settings.gemini_api_key is None:
        # Say exactly what to fix, instead of letting a vague SDK error surface later.
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env in the project folder (see .env.example).")
    # Built once on first use and then reused, so all requests share one connection pool.
    # The key is passed explicitly because the SDK would silently prefer GOOGLE_API_KEY
    # over GEMINI_API_KEY if both happened to be set on this machine.
    return genai.Client(api_key=settings.gemini_api_key.get_secret_value())


def ask_gemini(prompt: str) -> str:
    """Send one prompt to Gemini and return its text answer."""
    # Outside the try below: a missing setting is our misconfiguration, not a Gemini failure.
    client = _client()
    if not settings.gemini_model:
        raise RuntimeError("GEMINI_MODEL is not set. Add it to .env in the project folder (see .env.example).")

    try:
        interaction = client.interactions.create(
            model=settings.gemini_model,
            input=prompt,
            # Don't let Google keep this conversation for later retrieval; we don't need it.
            # (On the free tier, Google's data-use terms still apply to what we send.)
            store=False,
        )
    except Exception as exc:
        # google-genai 3.3.0 doesn't publicly export the Interactions API's error class,
        # so catch broadly, but only around this single network call.
        raise GeminiError(str(exc)) from exc

    if not interaction.output_text:
        raise GeminiError("Gemini returned no text.")
    return interaction.output_text
