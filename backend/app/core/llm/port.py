"""What the app needs from a language model, independent of any provider.

The composition root (bootstrap.py) picks the adapter that implements it (today GeminiModel, in
gemini.py) and hands it to the code that needs it. Nothing else imports a provider.
"""

from collections.abc import Iterator
from typing import Any, Protocol

from app.core.errors import ExternalServiceError
from app.core.llm.messages import Message, ReasoningEffort, ToolSpec, Usage


class LlmError(ExternalServiceError):
    """The model was called but couldn't give a usable answer (bad key, quota, model error, network...)."""


class LlmStream(Protocol):
    """One streamed answer. Loop over it for the text as it arrives; afterwards `.messages` holds
    everything the model produced (text, tool calls, reasoning), and `.usage` the token counts."""

    text: str
    messages: list[Message]
    usage: Usage

    def __iter__(self) -> Iterator[str]: ...


class LanguageModel(Protocol):
    def ask_for_json(self, prompt: str, schema: dict[str, Any], system_instruction: str) -> str:
        """Structured output: the answer is JSON shaped by `schema`. Returns the JSON text."""
        ...

    def stream_with_tools(
        self,
        history: list[Message],
        tools: list[ToolSpec],
        system_instruction: str,
        effort: ReasoningEffort | None = None,
    ) -> LlmStream:
        """One step of a tool-using conversation, streamed. `history` is the whole conversation so far."""
        ...
