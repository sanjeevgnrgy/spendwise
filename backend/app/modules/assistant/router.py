from fastapi import APIRouter, HTTPException

from app.core.llm import GeminiError
from app.modules.assistant import service
from app.modules.assistant.schemas import AskRequest, AskResponse

# The tag groups this module's routes under one heading in /docs.
router = APIRouter(tags=["assistant"])


@router.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    # A plain `def`, not `async def`: the Gemini call blocks while it waits, and FastAPI
    # runs plain functions in a worker thread so other requests aren't stuck behind it.
    try:
        answer = service.answer(body.prompt)
    except GeminiError as exc:
        # 502 means "a service we depend on failed", which is different from a bug here (500).
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AskResponse(answer=answer)
