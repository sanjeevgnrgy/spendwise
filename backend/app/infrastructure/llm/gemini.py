"""The Gemini adapter: Google's Gemini answering the core/llm language-model port (infrastructure, adapter).

The only code that calls Google's SDK. It sends each request (with our timeout and retry rules), turns every
SDK failure into LlmError, and reads streamed answers. The wire format itself (steps, function declarations,
putting streamed pieces back together) lives in gemini_wire.py. Swapping providers means writing another
adapter like this one.

An LlmError raised here carries Google's own words, a plain string: they reach the server log, never a person
(D180: web/problems.py and the AG-UI stream send a generic text instead).

The composition root (bootstrap.py) builds one GeminiModel with the API key and model name from the settings
and injects it; nothing else imports this file.
"""

import threading
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from google import genai
from google.genai import types
from pydantic import SecretStr

from app.core.llm.messages import Message, ReasoningEffort, ToolSpec, Usage
from app.core.llm.port import Attachment, LlmError
from app.infrastructure.llm.gemini_wire import EventType, StepAssembler, to_declaration, to_input, to_steps

# The SDK's defaults (5 attempts, waits of up to 60 s) can leave a request hanging for many minutes while
# Gemini is down. Give up on an attempt after 60 s and try at most twice. 60 s, not less: a function-calling
# step can take 20-30 s while the model thinks.
TIMEOUT_MS = 60_000
ATTEMPTS = 2
# Retry only when Google's side failed (5xx), e.g. "high demand". Never on 429 (quota used up): the SDK then
# sleeps for as long as Google's retry-after-ms header asks, with no upper limit and no timeout, so the request
# looked hung. Failing at once logs the quota message (a person is told the service failed: D180).
RETRY_STATUS_CODES = (500, 502, 503, 504)
JSON_MIME_TYPE = "application/json"

# Say exactly what to fix, instead of letting a vague SDK error surface later.
MISSING_KEY = "GEMINI_API_KEY is not set. Add it to .env in the project folder (see .env.example)."
MISSING_MODEL = "GEMINI_MODEL is not set. Add it to .env in the project folder (see .env.example)."
NO_TEXT = "Gemini returned no text."
STREAM_FAILED = "Gemini reported an error."

# Makes the SDK client from an API key. Replaceable, so the adapter can run against a fake client.
ClientFactory = Callable[[str], genai.Client]


def new_client(api_key: str) -> genai.Client:
    """A Gemini client with SpendWise's timeout and retry rules: GeminiModel's default client factory."""
    # The key is passed explicitly because the SDK would silently prefer GOOGLE_API_KEY over GEMINI_API_KEY
    # if both happened to be set on this machine.
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=ATTEMPTS, http_status_codes=list(RETRY_STATUS_CODES)),
        ),
    )


class GeminiModel:
    """The language-model port (port.py), answered by Gemini. Built once, by the composition root.

    It has both of the port's methods (structured output and streamed tool calling), so it fits wherever
    either is needed. The client isn't made here but on the first model call, and then reused, so all
    requests share one connection pool. The app therefore starts, and every route that doesn't use the model
    works, without a key; a missing key or model name is reported on the first model call, with the fix.
    """

    def __init__(
        self, api_key: SecretStr | None, model: str | None, client_factory: ClientFactory = new_client
    ) -> None:
        """Remember the key, the model name and how to make a client; nothing is checked or connected yet."""
        self._api_key = api_key
        self._model = model
        self._client_factory = client_factory
        self._client: genai.Client | None = None
        # Requests run in parallel worker threads: only one of them may make the shared client.
        self._client_lock = threading.Lock()

    def ask_for_json(
        self, prompt: str, schema: dict[str, Any], system_instruction: str, attachments: Sequence[Attachment] = ()
    ) -> str:
        """Structured output: Gemini's answer to `prompt` (and any attached files) as JSON text shaped by `schema`.

        Raises LlmError if Gemini fails or returns no text, RuntimeError if the key or model isn't configured.
        """
        interaction = self._create(
            # The files first (an image or a PDF each), then the prompt about them.
            input=to_input(prompt, attachments),
            system_instruction=system_instruction,
            # Gemini can only produce output that fits this JSON schema ("constrained decoding"),
            # so we get the fields and types we asked for instead of free-form prose.
            response_format={"type": "text", "mime_type": JSON_MIME_TYPE, "schema": schema},
        )
        if not interaction.output_text:
            raise LlmError(NO_TEXT)
        return interaction.output_text

    def stream_with_tools(
        self,
        history: list[Message],
        tools: list[ToolSpec],
        system_instruction: str,
        effort: ReasoningEffort | None = None,
    ) -> GeminiStream:
        """One step of a tool-using conversation, streamed: the answer may be text, tool calls, or both.

        `history` is the whole conversation so far: we don't let Google store it, so it's resent every time.
        Loop over the result for the text as it arrives, then read `.messages` for everything, tool calls
        included. Raises LlmError if the request fails, RuntimeError if the key or model isn't configured.
        """
        request: dict[str, Any] = {
            "input": to_steps(history),
            "tools": [to_declaration(tool) for tool in tools],
            "system_instruction": system_instruction,
        }
        if effort:
            request["generation_config"] = {"thinking_level": effort.value}
        # The request is sent now; the answer is read as the caller loops over the stream.
        return GeminiStream(self._create(stream=True, **request))

    def _shared_client(self) -> genai.Client:
        """The client, made on first use and then reused. Raises RuntimeError if there's no API key."""
        with self._client_lock:
            if self._client is None:
                if self._api_key is None:
                    raise RuntimeError(MISSING_KEY)
                self._client = self._client_factory(self._api_key.get_secret_value())
            return self._client

    def _create(self, **request: Any) -> Any:
        """Send one request to Gemini. Returns the whole interaction, or with stream=True, an event iterator.

        Raises RuntimeError if the key or model isn't configured, and LlmError if the call itself fails.
        """
        # Outside the try below: a missing setting is our misconfiguration, not a Gemini failure.
        client = self._shared_client()
        if not self._model:
            raise RuntimeError(MISSING_MODEL)
        try:
            return client.interactions.create(
                model=self._model,
                # Don't let Google keep this conversation for later retrieval; we don't need it.
                # (On the free tier, Google's data-use terms still apply to what we send.)
                store=False,
                **request,
            )
        except Exception as exc:
            # google-genai 3.3.0 doesn't publicly export the Interactions API's error class,
            # so catch broadly, but only around this single network call.
            raise LlmError(str(exc)) from exc


class GeminiStream:
    """One Gemini response, streamed: the port's LlmStream.

    Loop over it to get the answer's text piece by piece, as Gemini writes it. Once the loop has ended,
    `.messages` holds everything the model produced (text, tool calls, reasoning) as neutral messages, and
    `.usage` the token counts.
    """

    def __init__(self, events: Any) -> None:
        """Wrap the SDK's event stream; nothing is read until the caller loops."""
        self._events = events  # the SDK's event stream: one parsed Server-Sent Event per item
        self.text = ""
        self.messages: list[Message] = []
        self.usage = Usage()

    def __iter__(self) -> Iterator[str]:
        """Yield the answer's text as it arrives; when the stream ends, fill `.messages`.

        Raises LlmError if Gemini reports an error, the connection breaks mid-answer, or a function call's
        arguments aren't valid JSON.
        """
        assembler = StepAssembler()
        try:
            # `with` closes the HTTP connection even if the caller stops reading early.
            with self._events:
                for event in self._events:
                    text = self._read(event, assembler)
                    if text is not None:
                        self.text += text
                        yield text
            self.messages = assembler.messages()
        except LlmError:
            raise
        except Exception as exc:
            raise LlmError(str(exc)) from exc

    def _read(self, event: Any, assembler: StepAssembler) -> str | None:
        """Take in one streamed event. Returns text of the answer to pass on, or None.

        Raises LlmError if the event is Gemini reporting an error. Event types we don't use are skipped.
        """
        match getattr(event, "event_type", None):
            case EventType.STEP_START:
                # The step's outline: its type and, for a function call, the name and id.
                assembler.start(event.index, event.step.model_dump())
            case EventType.STEP_DELTA:
                return assembler.add(event.index, event.delta)
            case EventType.COMPLETED:
                # Only the token counts: unlike a non-streamed response, this final event doesn't repeat the steps.
                usage = event.interaction.usage
                if usage is not None:
                    self.usage = Usage(input_tokens=usage.total_input_tokens, output_tokens=usage.total_output_tokens)
            case EventType.ERROR:
                raise LlmError(event.error.message if event.error else STREAM_FAILED)
        return None
