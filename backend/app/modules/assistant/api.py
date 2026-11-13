"""HTTP routes for the assistant. They translate HTTP (and AG-UI) into the use cases."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.dependencies import ClockDep
from app.modules.assistant import agui, parse
from app.modules.assistant.schemas import ChatRequest, ChatResponse, ParseRequest, ParseResponse
from app.modules.assistant.turns import Assistant


def create_router(assistant: Assistant) -> APIRouter:
    """The routes, with the use cases handed in (constructor injection) rather than found globally."""
    # The tag groups this module's routes under one heading in /docs.
    router = APIRouter(tags=["assistant"])

    # Plain `def`, not `async def`: the model call blocks while it waits, and FastAPI runs plain
    # functions in a worker thread so other requests aren't stuck behind it.
    @router.post("/parse")
    def parse_expense(body: ParseRequest, clock: ClockDep) -> ParseResponse:
        # Suggests an expense from the text but saves nothing.
        return parse.parse_expense_text(assistant.bus, assistant.llm, body.text, clock.today())

    @router.post("/chat")
    def chat(body: ChatRequest, clock: ClockDep) -> ChatResponse:
        # Unlike /parse, this can change data: the agent may add, update or delete expenses through its tools.
        thread_id, finished = assistant.chat(body.message, body.thread_id, clock.today())
        return ChatResponse(thread_id=thread_id, reply=finished.reply, tool_calls=finished.tool_calls)

    # The same agent as /chat, but the reply is streamed as AG-UI events over Server-Sent Events, so the
    # browser can show it while the model is still writing. The run is checked first (agui.read_request):
    # a bad body or thread id is a normal 422; anything that goes wrong once streaming has begun is a
    # RUN_ERROR event.
    @router.post("/agent", response_class=EventSourceResponse)
    def agent_run(request: Annotated[agui.AgentRequest, Depends(agui.read_request)], clock: ClockDep) -> Iterator[ServerSentEvent]:
        # A plain (sync) generator: FastAPI runs it in a worker thread, and adds a ": ping" comment every
        # 15 s while the agent is quiet (e.g. running tools), so proxies don't close the connection.
        for event in agui.stream(request, assistant, clock.today()):
            # AG-UI's JSON (camelCase field names) as the event's `data:` line.
            yield ServerSentEvent(raw_data=event.model_dump_json(by_alias=True, exclude_none=True))

    return router
