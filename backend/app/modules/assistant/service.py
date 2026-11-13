from datetime import date

from sqlmodel import Session

from app.core import llm
from app.core.errors import BusinessRuleError

# Another module's public interface: the only way in to it.
from app.modules import categories
from app.modules.assistant import parse
from app.modules.assistant.schemas import ParseResponse


def answer(prompt: str) -> str:
    # Just a pass-through today. The orchestrator logic (tools, context, safety) grows
    # here in later phases, keeping the router free of business logic.
    return llm.ask_gemini(prompt)


def parse_expense_text(session: Session, text: str) -> ParseResponse:
    # The real category names, so Gemini can only pick one that exists.
    names = [c.name for c in categories.list_categories(session)]
    if not names:
        raise BusinessRuleError("There are no categories yet. Add some (or run backend/seed.py) first.")
    # The server's date, so "yesterday" means something. Per-user time zones can come with auth.
    parsed = parse.parse_expense(text, today=date.today(), category_names=names)
    return ParseResponse(expense=parsed, missing_fields=parse.missing_fields(parsed))
