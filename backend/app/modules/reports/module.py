"""How the composition root plugs this module in: its use case and routes. Nothing else uses it.

The reports module's wiring. It has no commands, queries or tables of its own (it reads through the expenses and
categories modules' queries), so it isn't in bootstrap.MODULES. bootstrap.py builds MonthlyReports with
create_reports() (for the MCP tool get_monthly_report too) and mounts the router from create_router().
"""

from fastapi import APIRouter

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.skills import SkillLibrary
from app.modules.reports import api
from app.modules.reports.application.monthly_reports import MonthlyReports


def create_reports(bus: MessageBus, skills: SkillLibrary, clock: Clock) -> MonthlyReports:
    """The monthly reports use case, around the bus, the skill library (whose script works the figures out) and the
    clock (today, for the running month's daily average)."""
    return MonthlyReports(bus, skills, clock)


def create_router(reports: MonthlyReports) -> APIRouter:
    """The reports routes, around the use case."""
    return api.create_router(reports)


__all__ = ["create_reports", "create_router"]
