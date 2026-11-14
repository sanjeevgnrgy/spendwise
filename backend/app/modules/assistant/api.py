"""HTTP routes for the assistant. They translate HTTP (and AG-UI) into the use cases.

The adapter layer, with no rules of its own:
- POST /parse reads an expense out of a short note and saves nothing (parse.ExpenseParser);
- POST /chat answers a message in one JSON reply (turns.Assistant.chat);
- POST /agent runs the same agent, streamed as AG-UI events over Server-Sent Events (agui_request.py reads
  the run, agui.py writes the events). The web app's chat panel uses this one.

module.create_router builds the router at startup, and main.py mounts it under /api/v1.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.core.dependencies import ClockDep
from app.modules.assistant import agui
from app.modules.assistant.agui_request import AgentRequest, read_request
from app.modules.assistant.parse import ExpenseParser
from app.modules.assistant.schemas import ChatRequest, ChatResponse, ParseRequest, ParseResponse
from app.modules.assistant.turns import Assistant

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
    @router.post("/parse")
    def parse_expense(body: ParseRequest, clock: ClockDep) -> ParseResponse:
        # Suggests an expense from the text but saves nothing. No categories yet is a 422 (BusinessRuleError);
        # a model that fails or answers in the wrong shape is a 502 (LlmError).
        return parser.parse(body.text, clock.today())

    # One message in, the whole reply out as one JSON body: no streaming, no cards or buttons.
    @router.post("/chat")
    def chat(body: ChatRequest, clock: ClockDep) -> ChatResponse:
        # Unlike /parse, this can change data: the agent may add, update or delete expenses through its tools.
        # There are no buttons here, so a delete needs the user's "yes" in words (see prompts.py, text chat).
        # A thread_id the server doesn't know is a 404 rather than a silent new conversation.
        thread_id, finished = assistant.chat(body.message, body.thread_id, clock.today())
        return ChatResponse(thread_id=thread_id, reply=finished.reply, tool_calls=finished.tool_calls)

    # The same agent as /chat, but the reply is streamed as AG-UI events over Server-Sent Events, so the
    # browser can show it while the model is still writing. The run is checked first
    # (agui_request.read_request): a bad body or thread id is a normal 422; anything that goes wrong once
    # streaming has begun is a RUN_ERROR event.
    @router.post("/agent", response_class=EventSourceResponse)
    def agent_run(
        request: Annotated[AgentRequest, Depends(read_request)], clock: ClockDep
    ) -> Iterator[ServerSentEvent]:
        # A plain (sync) generator: FastAPI runs it in a worker thread, and adds a ": ping" comment every
        # 15 s while the agent is quiet (e.g. running tools), so proxies don't close the connection.
        for event in agui.stream(request, assistant, clock.today()):
            # AG-UI's JSON (camelCase field names) as the event's `data:` line.
            yield ServerSentEvent(raw_data=event.model_dump_json(by_alias=True, exclude_none=True))

    return router
