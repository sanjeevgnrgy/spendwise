"""How the composition root plugs this module in: its handlers, routes, tables and tools adapter.

bootstrap.py uses everything here: it registers the handlers on the bus, creates an McpExpenseTools
(in-process, or remote with MCP_URL) and passes it to create_router with the language model and the receipts
module's ReceiptExtractor, and hands TABLES to the migrations. ExpenseTools is the port that adapter implements,
for anyone who builds another. Nothing else in the module is meant to be imported from outside.
"""

from fastapi import APIRouter

from app.core.cqrs import MessageBus
from app.core.llm import LanguageModel
from app.modules import receipts
from app.modules.assistant.api import routes
from app.modules.assistant.application.assistant import Assistant
from app.modules.assistant.application.expense_parser import ExpenseParser
from app.modules.assistant.approvals.commands.request_approval import RequestApproval, request_approval
from app.modules.assistant.approvals.commands.restore_approval import RestoreApproval, restore_approval
from app.modules.assistant.approvals.commands.take_approval import TakeApproval, take_approval
from app.modules.assistant.approvals.persistence.tables import TABLES
from app.modules.assistant.tools.mcp_adapter import McpExpenseTools
from app.modules.assistant.tools.port import ExpenseTools


def register_handlers(bus: MessageBus) -> None:
    """Register a handler for each of the module's commands: the three that manage delete cards."""
    bus.register(RequestApproval, request_approval)
    bus.register(TakeApproval, take_approval)
    bus.register(RestoreApproval, restore_approval)


def create_router(
    bus: MessageBus, tools: ExpenseTools, llm: LanguageModel, receipt_reader: receipts.ReceiptExtractor
) -> APIRouter:
    """The assistant's routes (/parse, /chat, /agent), around the use cases built from what's passed in.

    The model is used both ways: the agent's tool calling (Assistant) and /parse's structured output
    (ExpenseParser); each is given only the side it needs. `receipt_reader` reads a receipt attached in the web panel.
    """
    assistant = Assistant(bus=bus, tools=tools, llm=llm, receipts=receipt_reader)
    return routes.create_router(assistant, ExpenseParser(bus=bus, llm=llm))


__all__ = ["TABLES", "ExpenseTools", "McpExpenseTools", "create_router", "register_handlers"]
