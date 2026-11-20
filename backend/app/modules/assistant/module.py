"""How the composition root plugs this module in: its handlers, routes, tables and adapters.

bootstrap.py uses everything here: it registers the handlers on the bus, creates an McpExpenseTools (this app's MCP
server, in-process) and an A2AReceiptReader (the receipt agent, over A2A), and passes them to create_router with the
language model and the receipts module's ReceiptFiles, and hands TABLES to the migrations. ExpenseTools and
ReceiptReader are the ports those adapters implement, for anyone who builds another (a check's fake). Nothing else in
the module is meant to be imported from outside.
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
from app.modules.assistant.receipt_agent.a2a_client import A2AReceiptReader
from app.modules.assistant.receipt_agent.port import ReceiptReader
from app.modules.assistant.tools.mcp_adapter import McpExpenseTools
from app.modules.assistant.tools.port import ExpenseTools


def register_handlers(bus: MessageBus) -> None:
    """Register a handler for each of the module's commands: the three that manage delete cards."""
    bus.register(RequestApproval, request_approval)
    bus.register(TakeApproval, take_approval)
    bus.register(RestoreApproval, restore_approval)


def create_router(
    bus: MessageBus,
    tools: ExpenseTools,
    llm: LanguageModel,
    receipt_files: receipts.ReceiptFiles,
    receipt_reader: ReceiptReader,
) -> APIRouter:
    """The assistant's routes (/parse, /chat, /agent), around the use cases built from what's passed in.

    The model is used both ways: the agent's tool calling (Assistant) and /parse's structured output
    (ExpenseParser); each is given only the side it needs. A receipt attached in the web panel is taken from
    `receipt_files` (for its owner only) and read by `receipt_reader`.
    """
    assistant = Assistant(
        bus=bus, tools=tools, llm=llm, receipt_files=receipt_files, receipt_reader=receipt_reader
    )
    return routes.create_router(assistant, ExpenseParser(bus=bus, llm=llm))


__all__ = [
    "TABLES",
    "A2AReceiptReader",
    "ExpenseTools",
    "McpExpenseTools",
    "ReceiptReader",
    "create_router",
    "register_handlers",
]
