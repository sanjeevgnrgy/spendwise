"""HTTP routes for the assistant. Gemini failures become 502 in core/errors.py, so no try/except here."""

from collections.abc import Iterator

from ag_ui.core import RunAgentInput
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.db import SessionDep
from app.modules.assistant import service
from app.modules.assistant.schemas import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    ParseRequest,
    ParseResponse,
    ThreadRead,
)

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


@router.post("/chat")
def chat(body: ChatRequest, session: SessionDep) -> ChatResponse:
    # Unlike /parse, this can change data: the agent may add, update or delete expenses via MCP tools.
    # It must stay a plain `def` (run in a worker thread): the agent calls this same app's /mcp
    # endpoint, and an `async def` that blocked the server's event loop while waiting would deadlock.
    return service.chat(session, body.message, body.thread_id)


# The same agent as /chat, but the reply is streamed as AG-UI events over Server-Sent Events,
# so the browser can show it while Gemini is still writing. A missing or malformed field in the
# body is still a normal 422; anything that goes wrong once streaming has begun is a RUN_ERROR event.
@router.post("/agent", response_class=EventSourceResponse)
def agent_run(body: RunAgentInput, session: SessionDep) -> Iterator[ServerSentEvent]:
    # A plain (sync) generator, for the same reason /chat is a plain `def`: FastAPI runs it in a
    # worker thread, so the agent's calls to this app's own /mcp endpoint can't deadlock.
    # FastAPI keeps the database session open until the stream ends, and adds a ": ping" comment
    # every 15 s while the agent is quiet (e.g. running tools), so proxies don't close the connection.
    for event in service.agent_run(session, body):
        # AG-UI's JSON (camelCase field names, empty fields left out) as the event's `data:` line.
        yield ServerSentEvent(raw_data=event.model_dump_json(by_alias=True))


@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, session: SessionDep) -> ThreadRead:
    return service.get_thread(session, thread_id)
