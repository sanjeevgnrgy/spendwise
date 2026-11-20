"""One long-lived event loop for all A2A work: BackgroundLoop (infrastructure, used by agents.A2AAgents).

The A2A SDK is async, but its callers run in plain worker threads (FastAPI runs sync routes and streams there). Every
call is handed to the same event loop, on a thread of its own, and the caller waits for the result. One loop, not one
per call, because the agents run inside the backend (D207): their request handlers, task stores and locks are created
once and must always be used from the loop they belong to, however many requests arrive at once.
"""

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

THREAD_NAME = "a2a-loop"


class BackgroundLoop:
    """An event loop on a daemon thread, started on first use; run() waits for a coroutine on it."""

    def __init__(self) -> None:
        """Nothing starts yet: the thread and its loop are made by the first run()."""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def run(self, coroutine: Coroutine[Any, Any, T], timeout: float) -> T:
        """Run `coroutine` on the loop and return its result. Raises what it raises, or TimeoutError after `timeout`
        seconds (the coroutine is then cancelled)."""
        future = asyncio.run_coroutine_threadsafe(asyncio.wait_for(coroutine, timeout), self._started())
        return future.result()

    def _started(self) -> asyncio.AbstractEventLoop:
        """The loop, starting its thread the first time."""
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name=THREAD_NAME, daemon=True).start()
                self._loop = loop
            return self._loop
