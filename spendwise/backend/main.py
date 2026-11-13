from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.llm import GeminiError, ask_gemini

# Copy spendwise/.env into environment variables. Variables already set in the real
# environment win, so a server can configure the app without any .env file at all.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# One app object for the whole backend. Uvicorn finds it by name ("backend.main:app").
app = FastAPI(title="SpendWise API", version="0.2.0")


class AskRequest(BaseModel):
    # The upper limit matters because every character is sent to Gemini and paid for as tokens.
    prompt: str = Field(min_length=1, max_length=4000)


class AskResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict[str, str]:
    # Does no real work, so a monitor can call it often to check the server is up.
    return {"status": "ok"}


@app.get("/hello/{name}")
def hello(name: str) -> dict[str, str]:
    # The argument must be named like {name} in the path; that's how FastAPI
    # knows to fill it from the URL instead of from a query string.
    return {"message": f"Hello, {name}!"}


@app.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    # A plain `def`, not `async def`: the Gemini call blocks while it waits, and FastAPI
    # runs plain functions in a worker thread so other requests aren't stuck behind it.
    try:
        answer = ask_gemini(body.prompt)
    except GeminiError as exc:
        # 502 means "a service we depend on failed", which is different from a bug here (500).
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AskResponse(answer=answer)
