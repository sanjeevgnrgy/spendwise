"""HTTP routes for the assistant. Gemini failures become 502 in core/errors.py, so no try/except here."""

from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.assistant import service
from app.modules.assistant.schemas import AskRequest, AskResponse, ParseRequest, ParseResponse

# The tag groups this module's routes under one heading in /docs.
router = APIRouter(tags=["assistant"])


# Plain `def`, not `async def`: the Gemini call blocks while it waits, and FastAPI runs
# plain functions in a worker thread so other requests aren't stuck behind it.
@router.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    return AskResponse(answer=service.answer(body.prompt))


@router.post("/parse")
def parse_expense(body: ParseRequest, session: SessionDep) -> ParseResponse:
    # Suggests an expense from the text but saves nothing. Saving is a separate, deliberate
    # step (POST /expenses), so a misread note never lands in your data on its own.
    return service.parse_expense_text(session, body.text)
