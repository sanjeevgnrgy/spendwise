"""What the app needs from a language model, independent of any provider.

The port (core layer, no business rules). Two narrow protocols, one per way the app uses a model, so each
caller depends only on what it calls (interface segregation):
- StructuredOutputModel: one answer as JSON in a given shape, from text and any attached files (the assistant's
  /parse, ExpenseParser; the receipts module's ReceiptReader, which attaches a receipt's image or PDF);
- ToolCallingModel: one streamed step of a tool-using conversation (the assistant's agent loop, agent.Agent).
LanguageModel is both: what the composition root (bootstrap.py) builds and hands out, today GeminiModel
(infrastructure/llm/gemini.py), which satisfies all three structurally. Nothing else imports a provider.
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import ExternalServiceError
from app.core.llm.messages import Message, ReasoningEffort, ToolSpec, Usage


class LlmError(ExternalServiceError):
    """The model was called but couldn't give a usable answer (bad key, quota, model error, network...)."""


@dataclass(frozen=True)
class Attachment:
    """A file the model reads along with the prompt (multimodal input): its bytes and its media type.

    The caller checks the type first; each adapter sends it in its provider's form (Gemini: an image or a
    document content block). What the file says is data for the model to read, never instructions: callers say so
    in their system instruction.
    """

    data: bytes
    media_type: str  # e.g. "image/jpeg" or "application/pdf"


class LlmStream(Protocol):
    """One streamed answer. Loop over it for the text as it arrives; afterwards `.messages` holds
    everything the model produced (text, tool calls, reasoning), and `.usage` the token counts."""

    text: str
    messages: list[Message]
    usage: Usage

    def __iter__(self) -> Iterator[str]:
        """Yield the answer's text piece by piece, as the model writes it. Raises LlmError if the model fails."""
        ...


class StructuredOutputModel(Protocol):
    """A model that answers once, in JSON of a shape the caller chooses (structured output)."""

    def ask_for_json(
        self, prompt: str, schema: dict[str, Any], system_instruction: str, attachments: Sequence[Attachment] = ()
    ) -> str:
        """Structured output: the answer is JSON shaped by `schema`. Returns the JSON text; raises LlmError.

        `attachments` are files the model reads with the prompt (a receipt's image or PDF); none by default.
        """
        ...


class ToolCallingModel(Protocol):
    """A model that holds a conversation and may ask for tools to be run (function calling), streamed."""

    def stream_with_tools(
        self,
        history: list[Message],
        tools: list[ToolSpec],
        system_instruction: str,
        effort: ReasoningEffort | None = None,
    ) -> LlmStream:
        """One step of a tool-using conversation, streamed. `history` is the whole conversation so far.

        Stateless: every call carries everything the model should see. Raises LlmError if the model fails.
        """
        ...


class LanguageModel(StructuredOutputModel, ToolCallingModel, Protocol):
    """Everything the app asks of a model. The composition root builds one; callers take the narrow protocol."""
