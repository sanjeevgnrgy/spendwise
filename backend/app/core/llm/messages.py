"""A conversation in SpendWise's own terms, independent of any LLM provider.

Before this, the chat history was stored exactly as Gemini's API writes it, so changing provider would
have meant migrating every stored conversation. Now the agent, the history and the database speak
these types, and each provider's adapter (gemini.py) translates at the edge.
"""

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class MessageKind(StrEnum):
    USER_TEXT = "user_text"
    ASSISTANT_TEXT = "assistant_text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REASONING = "reasoning"


class _Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class UserText(_Message):
    kind: Literal[MessageKind.USER_TEXT] = MessageKind.USER_TEXT
    text: str


class AssistantText(_Message):
    kind: Literal[MessageKind.ASSISTANT_TEXT] = MessageKind.ASSISTANT_TEXT
    text: str


class ToolCall(_Message):
    """The model asks for a tool to run."""

    kind: Literal[MessageKind.TOOL_CALL] = MessageKind.TOOL_CALL
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(_Message):
    """What a tool returned, sent back to the model."""

    kind: Literal[MessageKind.TOOL_RESULT] = MessageKind.TOOL_RESULT
    call_id: str
    name: str
    output: str
    is_error: bool = False


class Reasoning(_Message):
    """The model's private reasoning, kept only so it can be handed back to the same provider.

    Providers need it to carry on a line of thought after a tool call (Gemini's thought signature,
    for example). Its content is the provider's own, so it's opaque here and other providers skip it.
    """

    kind: Literal[MessageKind.REASONING] = MessageKind.REASONING
    provider: str
    opaque: dict[str, Any]


Message = Annotated[UserText | AssistantText | ToolCall | ToolResult | Reasoning, Field(discriminator="kind")]
# Reads stored or received JSON back into the right message types.
messages_adapter: TypeAdapter[list[Message]] = TypeAdapter(list[Message])


class ToolSpec(BaseModel):
    """A tool the model may call: its name, what it does, and its arguments as JSON Schema."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    parameters: dict[str, Any]


class ReasoningEffort(StrEnum):
    """How hard the model thinks before answering: deeper is slower and uses more of the quota."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Usage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
