"""The LLM port: what the rest of the app may use to talk to a language model.

Core layer. Callers use the neutral types from messages.py and the narrowest interface from port.py they
need (StructuredOutputModel, ToolCallingModel, or LanguageModel for both), plus schema.py's shared pieces of a
structured-output schema; the composition root (bootstrap.py) decides which provider answers (today:
infrastructure/llm/gemini.GeminiModel, imported only there).
"""

from app.core.llm.messages import (
    AssistantText,
    Message,
    MessageKind,
    Reasoning,
    ReasoningEffort,
    ToolCall,
    ToolResult,
    ToolSpec,
    Usage,
    UserText,
    messages_adapter,
)
from app.core.llm.port import (
    Attachment,
    LanguageModel,
    LlmError,
    LlmStream,
    StructuredOutputModel,
    ToolCallingModel,
)
from app.core.llm.schema import DecimalText, restrict_to_choices

__all__ = [
    "AssistantText",
    "Attachment",
    "DecimalText",
    "LanguageModel",
    "LlmError",
    "LlmStream",
    "Message",
    "MessageKind",
    "Reasoning",
    "ReasoningEffort",
    "StructuredOutputModel",
    "ToolCall",
    "ToolCallingModel",
    "ToolResult",
    "ToolSpec",
    "Usage",
    "UserText",
    "messages_adapter",
    "restrict_to_choices",
]
