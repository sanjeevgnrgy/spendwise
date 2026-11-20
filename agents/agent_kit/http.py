"""Every agent's HTTP gate: the key check, the request size limit and no-store answers (ASGI middleware).

Part of the agent kit, wrapped around every route by server.build_agent_app. The SDK declares a card's security
scheme but doesn't check it (D197), so this does, before the JSON-RPC route reads anything: a request without
"Authorization: Bearer <the agent's key>" gets a 401, one without a Content-Length or larger than the agent's limit a
411 or 413. Only the Agent Card is open. Every answer carries Cache-Control: no-store, because it may hold a person's
data (a receipt, an amount).
"""

import hmac
from http import HTTPStatus

from pydantic import SecretStr
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# A JSON-RPC request carries a file as base64 (4 bytes for every 3), plus the request's data and the envelope: an
# agent that takes files allows request_limit(its largest file).
BASE64_GROWTH = 4 / 3
ENVELOPE_BYTES = 64 * 1024

NO_STORE = "no-store"
# Why a request was refused (English, for the client's log; never shown to a person).
NO_KEY = "a valid bearer key is required"
NO_LENGTH = "Content-Length is required"
TOO_LARGE = "the request is over {limit} bytes"
ASK_FOR_BEARER = {"WWW-Authenticate": "Bearer"}


def request_limit(largest_file: int = 0) -> int:
    """The largest request an agent accepts: its largest file as base64 (none by default), plus the envelope."""
    return int(largest_file * BASE64_GROWTH) + ENVELOPE_BYTES


class AgentGate:
    """Checks the key and the size of every request but those to `open_paths`, and marks every answer no-store."""

    def __init__(
        self, app: ASGIApp, key: SecretStr, open_paths: frozenset[str], max_request_bytes: int
    ) -> None:
        """Wrap `app`; `key` is the agent's key, `open_paths` the paths anyone may read (the Agent Card), and
        `max_request_bytes` the largest request it reads (request_limit)."""
        self._app = app
        self._expected = f"Bearer {key.get_secret_value()}".encode()
        self._open_paths = open_paths
        self._max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 401, 411 or 413 at once if the request may not go on; otherwise pass it on, marked no-store."""
        if scope["type"] != "http":  # lifespan events pass through
            await self._app(scope, receive, send)
            return
        refusal = None if scope["path"] in self._open_paths else self._refusal(Headers(scope=scope))
        if refusal is not None:
            await refusal(scope, receive, _no_store(send))
            return
        await self._app(scope, receive, _no_store(send))

    def _refusal(self, headers: Headers) -> JSONResponse | None:
        """The answer that refuses this request, or None if it may go on."""
        # compare_digest takes the same time wherever the first difference is, so the key can't be guessed by timing.
        if not hmac.compare_digest(headers.get("authorization", "").encode(), self._expected):
            return JSONResponse({"error": NO_KEY}, HTTPStatus.UNAUTHORIZED, ASK_FOR_BEARER)
        length = headers.get("content-length")
        if length is None or not length.isdigit():
            return JSONResponse({"error": NO_LENGTH}, HTTPStatus.LENGTH_REQUIRED)
        if int(length) > self._max_request_bytes:
            too_large = TOO_LARGE.format(limit=self._max_request_bytes)
            return JSONResponse({"error": too_large}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        return None


def _no_store(send: Send) -> Send:
    """`send`, with Cache-Control: no-store added to the answer's headers."""

    async def sending(message: Message) -> None:
        """Pass `message` on, adding the header to the start of the answer."""
        if message["type"] == "http.response.start":
            MutableHeaders(scope=message)["Cache-Control"] = NO_STORE
        await send(message)

    return sending
