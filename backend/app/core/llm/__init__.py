"""The LLM port: what the rest of the app may use to talk to a language model.

Core layer. Callers use the neutral types from messages.py and the narrowest interface from port.py they
need (StructuredOutputModel, ToolCallingModel, or LanguageModel for both); the composition root
(bootstrap.py) decides which provider answers (today: gemini.GeminiModel, imported only there).
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
from app.core.llm.port import LanguageModel, LlmError, LlmStream, StructuredOutputModel, ToolCallingModel

__all__ = [
    "AssistantText",
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
]
