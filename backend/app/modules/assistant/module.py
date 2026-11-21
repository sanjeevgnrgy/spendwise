"""How the composition root plugs this module in: its handlers, routes, tables and adapters.

bootstrap.py uses everything here: it registers the handlers on the bus, creates an McpExpenseTools (this app's MCP
server, in-process), and passes it to create_router with the language model, the receipts module's ReceiptFiles, the
app's remote agents and the clock (create_router builds the receipt reader around them, and the directory of agents
the model may delegate to, whose cards it reads at once: at startup), and hands TABLES to the migrations.
ExpenseTools is the port that adapter implements, for anyone who builds another (a check's fake). Nothing else in the
module is meant to be imported from outside.
"""

from fastapi import APIRouter

from app.core.agents import RemoteAgents
from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.llm import LanguageModel
from app.core.skills import SkillLibrary
from app.modules import receipts
from app.modules.assistant.api import routes
from app.modules.assistant.application.assistant import Assistant
from app.modules.assistant.application.expense_parser import ExpenseParser
from app.modules.assistant.approvals.commands.request_approval import RequestApproval, request_approval
from app.modules.assistant.approvals.commands.restore_approval import RestoreApproval, restore_approval
from app.modules.assistant.approvals.commands.take_approval import TakeApproval, take_approval
from app.modules.assistant.approvals.persistence.tables import TABLES as APPROVAL_TABLES
from app.modules.assistant.delegation import AgentDirectory, delegable_skills
from app.modules.assistant.delegation.commands.remember_task import RememberTask, remember_task
from app.modules.assistant.delegation.commands.take_task import TakeTask, take_task
from app.modules.assistant.delegation.persistence.tables import TABLES as DELEGATION_TABLES
from app.modules.assistant.receipt_agent.agent_reader import AgentReceiptReader
from app.modules.assistant.tools.mcp_adapter import McpExpenseTools
from app.modules.assistant.tools.port import ExpenseTools

# The module's tables, for the migrations: delete cards waiting for Approve, and agents' tasks waiting for an answer.
TABLES = (*APPROVAL_TABLES, *DELEGATION_TABLES)


def register_handlers(bus: MessageBus) -> None:
    """Register a handler for each of the module's commands: the three that manage delete cards, and the two that
    keep an agent's waiting task."""
    bus.register(RequestApproval, request_approval)
    bus.register(TakeApproval, take_approval)
    bus.register(RestoreApproval, restore_approval)
    bus.register(RememberTask, remember_task)
    bus.register(TakeTask, take_task)


def create_router(
    bus: MessageBus,
    tools: ExpenseTools,
    llm: LanguageModel,
    receipt_files: receipts.ReceiptFiles,
    agents: RemoteAgents,
    clock: Clock,
    skills: SkillLibrary,
) -> APIRouter:
    """The assistant's routes (/parse, /chat, /agent), around the use cases built from what's passed in.

    The model is used both ways: the agent's tool calling (Assistant) and /parse's structured output
    (ExpenseParser); each is given only the side it needs. A receipt attached in the web panel is taken from
    `receipt_files` (for its owner only) and read by the receipt agent, one of `agents`. The others' cards are read
    here, as the app starts, for the model to delegate to (D206); one that can't be read yet is tried again later.
    `skills` are offered to the model a level at a time (D208).
    """
    reader = AgentReceiptReader(agents)
    directory = AgentDirectory(agents, delegable_skills(bus), clock)
    directory.load()
    assistant = Assistant(
        bus=bus,
        tools=tools,
        llm=llm,
        receipt_files=receipt_files,
        receipt_reader=reader,
        directory=directory,
        agents=agents,
        skills=skills,
    )
    return routes.create_router(assistant, ExpenseParser(bus=bus, llm=llm))


__all__ = ["TABLES", "ExpenseTools", "McpExpenseTools", "create_router", "register_handlers"]
