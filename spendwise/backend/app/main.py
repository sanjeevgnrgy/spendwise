"""Composition root: the one place that knows every module and wires them into the app."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import create_db_and_tables

# Imported so their tables are registered before create_db_and_tables() runs.
# They have no HTTP routes yet; those come in a later phase.
from app.modules import categories, expenses  # noqa: F401
from app.modules.assistant.router import router as assistant_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Runs once at startup, before the first request is accepted.
    create_db_and_tables()
    yield


app = FastAPI(title="SpendWise API", version="0.3.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    # Does no real work, so a monitor can call it often to check the server is up.
    return {"status": "ok"}


app.include_router(assistant_router)
