"""How the composition root plugs this module in: its handlers, routes, tables and tools adapter.

bootstrap.py uses everything here: it registers the handlers on the bus, creates an McpExpenseTools
(in-process, or remote with MCP_URL) and passes it to create_router with the language model, and hands
TABLES to the migrations. ExpenseTools is the port that adapter implements, for anyone who builds another.
Nothing else in the module is meant to be imported from outside.
"""

from fastapi import APIRouter

from app.core.cqrs import MessageBus
from app.core.llm import LanguageModel
from app.modules.assistant import api, approvals
from app.modules.assistant.parse import ExpenseParser
from app.modules.assistant.tables import TABLES
from app.modules.assistant.tools import ExpenseTools, McpExpenseTools
from app.modules.assistant.turns import Assistant


def register_handlers(bus: MessageBus) -> None:
    """Register a handler for each of the module's commands: the three that manage delete cards."""
    bus.register(approvals.RequestApproval, approvals.request_approval)
    bus.register(approvals.TakeApproval, approvals.take_approval)
    bus.register(approvals.RestoreApproval, approvals.restore_approval)


def create_router(bus: MessageBus, tools: ExpenseTools, llm: LanguageModel) -> APIRouter:
    """The assistant's routes (/parse, /chat, /agent), around the use cases built from what's passed in.

    The model is used both ways: the agent's tool calling (Assistant) and /parse's structured output
    (ExpenseParser); each is given only the side it needs.
    """
    return api.create_router(Assistant(bus=bus, tools=tools, llm=llm), ExpenseParser(bus=bus, llm=llm))


__all__ = ["TABLES", "ExpenseTools", "McpExpenseTools", "create_router", "register_handlers"]
