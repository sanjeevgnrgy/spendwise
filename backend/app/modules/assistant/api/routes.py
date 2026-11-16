"""HTTP routes for the assistant. They translate HTTP (and AG-UI) into the use cases.

The adapter layer, with no rules of its own:
- POST /parse reads an expense out of a short note and saves nothing (application/expense_parser.py's
  ExpenseParser);
- POST /chat answers a message in one JSON reply (application/assistant.py's Assistant.chat);
- POST /agent runs the same agent, streamed as AG-UI events over Server-Sent Events (agui_request.py reads
  the run, agui_stream.py writes the events). The web app's chat panel uses this one.

/chat and /agent answer in the request's language (LanguageDep, from its Accept-Language): the model is asked to
reply in it, and everything the server writes (cards, chips, its own replies) is in it. Errors are written in it by
web/problems.py. module.create_router builds the router at startup, and main.py mounts it under /api/v1.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.modules.assistant.api import agui_stream
from app.modules.assistant.api.agui_request import AgentRequest, read_request
from app.modules.assistant.api.schemas import ChatRequest, ChatResponse, ParseRequest
from app.modules.assistant.application.assistant import Assistant
from app.modules.assistant.application.expense_parser import ExpenseParser, ParseResponse
from app.web.auth import CurrentUserDep
from app.web.dependencies import ClockDep, LanguageDep
from app.web.rate_limits import MODEL_QUOTA

# The tag that groups this module's routes under one heading in /docs.
TAG = "assistant"


def create_router(assistant: Assistant, parser: ExpenseParser) -> APIRouter:
    """The routes, with the use cases handed in (constructor injection) rather than found globally.

    The route functions are closures over `assistant` and `parser`, so whoever builds the router decides
    what's behind them (the real model and tools, or stand-ins).
    """
    router = APIRouter(tags=[TAG])

    # Plain `def`, not `async def`: the model call blocks while it waits, and FastAPI runs plain
    # functions in a worker thread so other requests aren't stuck behind it.
    # Each of the three calls the model, so each counts against the person's allowance (MODEL_QUOTA, D194): a 429
    # once it's spent.
    @router.post("/parse", dependencies=[MODEL_QUOTA])
    def parse_expense(body: ParseRequest, clock: ClockDep) -> ParseResponse:
        # Suggests an expense from the text but saves nothing. No categories yet is a 422 (BusinessRuleError);
        # a model that fails or answers in the wrong shape is a 502 (LlmError).
        return parser.parse(body.text, clock.today())

    # One message in, the whole reply out as one JSON body: no streaming, no cards or buttons.
    @router.post("/chat", dependencies=[MODEL_QUOTA])
    def chat(body: ChatRequest, principal: CurrentUserDep, clock: ClockDep, language: LanguageDep) -> ChatResponse:
        # Unlike /parse, this can change data: the agent may add, update or delete expenses through its tools.
        # There are no buttons here, so a delete needs the user's "yes" in words (see agent/prompts.py, text chat).
        # A thread_id the person doesn't have is a 404 rather than a silent new conversation. Everything acts for the
        # signed-in person: their threads, their expenses (D190, D191).
        owner = principal.user_id
        thread_id, finished = assistant.chat(owner, body.message, body.thread_id, clock.today(), language)
        return ChatResponse(thread_id=thread_id, reply=finished.reply, tool_calls=finished.tool_calls)

    # The same agent as /chat, but the reply is streamed as AG-UI events over Server-Sent Events, so the
    # browser can show it while the model is still writing. The run is checked first
    # (agui_request.read_request): a bad body or thread id is a normal 422; anything that goes wrong once
    # streaming has begun is a RUN_ERROR event.
    @router.post("/agent", response_class=EventSourceResponse, dependencies=[MODEL_QUOTA])
    def agent_run(
        request: Annotated[AgentRequest, Depends(read_request)],
        principal: CurrentUserDep,
        clock: ClockDep,
        language: LanguageDep,
    ) -> Iterator[ServerSentEvent]:
        # A plain (sync) generator: FastAPI runs it in a worker thread, and adds a ": ping" comment every
        # 15 s while the agent is quiet (e.g. running tools), so proxies don't close the connection.
        # The run acts for the signed-in person: their thread, their cards, their expenses (D190, D191).
        for event in agui_stream.stream(request, principal.user_id, assistant, clock.today(), language):
            # AG-UI's JSON (camelCase field names) as the event's `data:` line.
            yield ServerSentEvent(raw_data=event.model_dump_json(by_alias=True, exclude_none=True))

    return router
