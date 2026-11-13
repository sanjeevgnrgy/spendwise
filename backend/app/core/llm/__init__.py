"""The LLM port: what the rest of the app may use to talk to a language model.

Callers use the neutral types from messages.py and the LanguageModel interface from port.py; the
composition root (bootstrap.py) decides which provider answers (today: gemini.GeminiModel).
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
from app.core.llm.port import LanguageModel, LlmError, LlmStream

__all__ = [
    "AssistantText",
    "LanguageModel",
    "LlmError",
    "LlmStream",
    "Message",
    "MessageKind",
    "Reasoning",
    "ReasoningEffort",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
    "Usage",
    "UserText",
    "messages_adapter",
]
