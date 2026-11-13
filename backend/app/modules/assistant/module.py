"""How the composition root plugs this module in: its handlers, routes, tables and tools adapter."""

from fastapi import APIRouter

from app.core.cqrs import MessageBus
from app.core.llm import LanguageModel
from app.modules.assistant import api, approvals
from app.modules.assistant.tables import TABLES
from app.modules.assistant.tools import ExpenseTools, McpExpenseTools
from app.modules.assistant.turns import Assistant


def register_handlers(bus: MessageBus) -> None:
    bus.register(approvals.RequestApproval, approvals.request_approval)
    bus.register(approvals.TakeApproval, approvals.take_approval)
    bus.register(approvals.RestoreApproval, approvals.restore_approval)


def create_router(bus: MessageBus, tools: ExpenseTools, llm: LanguageModel) -> APIRouter:
    return api.create_router(Assistant(bus=bus, tools=tools, llm=llm))


__all__ = ["TABLES", "McpExpenseTools", "create_router", "register_handlers"]
